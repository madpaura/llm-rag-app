"""
Code parsing service using tree-sitter for C/C++ AST analysis.
Extracts functions, classes, structs and builds call graphs.
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import structlog
import re

logger = structlog.get_logger()

# Tree-sitter imports - will be initialized lazily
_c_parser = None
_cpp_parser = None


@dataclass
class CodeUnit:
    """Represents an extracted code unit (function, class, struct, file)."""
    unit_type: str  # function, method, class, struct, file
    name: str
    signature: Optional[str] = None
    code: str = ""
    start_line: int = 0
    end_line: int = 0
    language: str = "c"
    parent_name: Optional[str] = None
    children: List['CodeUnit'] = field(default_factory=list)
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _get_parser(language: str):
    """Get or create tree-sitter parser for the specified language."""
    global _c_parser, _cpp_parser
    
    try:
        import tree_sitter_c as tsc
        import tree_sitter_cpp as tscpp
        from tree_sitter import Language, Parser
        
        if language == "c":
            if _c_parser is None:
                _c_parser = Parser(Language(tsc.language()))
            return _c_parser
        else:  # cpp
            if _cpp_parser is None:
                _cpp_parser = Parser(Language(tscpp.language()))
            return _cpp_parser
    except ImportError as e:
        logger.error(f"Failed to import tree-sitter: {e}")
        raise ImportError(
            "tree-sitter packages not installed. Run: pip install tree-sitter tree-sitter-c tree-sitter-cpp"
        )


def _get_node_text(node, source_bytes: bytes) -> str:
    """Extract text from a tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')


def _get_language_from_extension(file_path: str) -> str:
    """Determine language from file extension."""
    ext = Path(file_path).suffix.lower()
    if ext in ['.c', '.h']:
        return 'c'
    elif ext in ['.cpp', '.cc', '.cxx', '.hpp', '.hxx', '.hh']:
        return 'cpp'
    return 'c'  # Default to C


class CodeParserService:
    """
    Service for parsing C/C++ source files using tree-sitter.
    Extracts functions, classes, structs and call relationships.
    """
    
    SUPPORTED_EXTENSIONS = {'.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx', '.hh'}
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is a supported C/C++ file."""
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> CodeUnit:
        """
        Parse a C/C++ file and extract all code units.
        
        Args:
            file_path: Path to the source file
            content: Optional file content (if not provided, reads from file_path)
            
        Returns:
            CodeUnit representing the file with nested children
        """
        if content is None:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        
        language = _get_language_from_extension(file_path)
        source_bytes = content.encode('utf-8')
        
        # Parse with tree-sitter
        parser = _get_parser(language)
        tree = parser.parse(source_bytes)
        
        # Create file-level code unit
        file_unit = CodeUnit(
            unit_type="file",
            name=Path(file_path).name,
            code=content,
            start_line=1,
            end_line=content.count('\n') + 1,
            language=language,
            metadata={"file_path": file_path}
        )
        
        # Extract includes
        file_unit.includes = self._extract_includes(tree.root_node, source_bytes)
        
        # Extract all code units
        self._extract_units(tree.root_node, source_bytes, file_unit, language)
        
        return file_unit
    
    def _extract_includes(self, root_node, source_bytes: bytes) -> List[str]:
        """Extract #include statements."""
        includes = []
        
        def traverse(node):
            if node.type == 'preproc_include':
                include_text = _get_node_text(node, source_bytes)
                # Extract the header name
                match = re.search(r'[<"]([^>"]+)[>"]', include_text)
                if match:
                    includes.append(match.group(1))
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return includes
    
    def _extract_units(
        self, 
        node, 
        source_bytes: bytes, 
        parent_unit: CodeUnit,
        language: str,
        class_name: Optional[str] = None
    ):
        """Recursively extract code units from AST."""
        
        for child in node.children:
            unit = None
            
            # Function definitions
            if child.type == 'function_definition':
                unit = self._extract_function(child, source_bytes, language, class_name)
                if unit:
                    parent_unit.children.append(unit)
            
            # Class definitions (C++)
            elif child.type == 'class_specifier':
                unit = self._extract_class(child, source_bytes, language)
                if unit:
                    parent_unit.children.append(unit)
            
            # Struct definitions
            elif child.type == 'struct_specifier':
                unit = self._extract_struct(child, source_bytes, language)
                if unit:
                    parent_unit.children.append(unit)
            
            # Declaration with function (for prototypes in headers)
            elif child.type == 'declaration':
                func_unit = self._try_extract_function_declaration(child, source_bytes, language)
                if func_unit:
                    parent_unit.children.append(func_unit)
            
            # Recurse into namespaces, etc.
            elif child.type in ['namespace_definition', 'linkage_specification']:
                self._extract_units(child, source_bytes, parent_unit, language, class_name)
            
            # Continue traversing for nested structures
            else:
                self._extract_units(child, source_bytes, parent_unit, language, class_name)
    
    def _extract_function(
        self, 
        node, 
        source_bytes: bytes, 
        language: str,
        class_name: Optional[str] = None
    ) -> Optional[CodeUnit]:
        """Extract a function definition."""
        try:
            # Get function name
            declarator = self._find_child_by_type(node, 'function_declarator')
            if not declarator:
                declarator = self._find_child_by_type(node, 'declarator')
            
            if not declarator:
                return None
            
            # Find the identifier (function name)
            name_node = self._find_descendant_by_type(declarator, 'identifier')
            if not name_node:
                name_node = self._find_descendant_by_type(declarator, 'field_identifier')
            
            if not name_node:
                return None
            
            func_name = _get_node_text(name_node, source_bytes)
            
            # Get return type
            return_type = ""
            type_node = self._find_child_by_type(node, 'primitive_type')
            if not type_node:
                type_node = self._find_child_by_type(node, 'type_identifier')
            if type_node:
                return_type = _get_node_text(type_node, source_bytes)
            
            # Get parameters
            params = self._extract_parameters(declarator, source_bytes)
            signature = f"{return_type} {func_name}({', '.join(params)})"
            
            # Get full code
            code = _get_node_text(node, source_bytes)
            
            # Extract function calls
            function_calls = self._extract_function_calls(node, source_bytes)
            
            unit_type = "method" if class_name else "function"
            
            return CodeUnit(
                unit_type=unit_type,
                name=func_name,
                signature=signature,
                code=code,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language,
                parent_name=class_name,
                function_calls=function_calls,
                metadata={
                    "return_type": return_type,
                    "parameters": params
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to extract function: {e}")
            return None
    
    def _extract_class(self, node, source_bytes: bytes, language: str) -> Optional[CodeUnit]:
        """Extract a class definition."""
        try:
            # Get class name
            name_node = self._find_child_by_type(node, 'type_identifier')
            if not name_node:
                return None
            
            class_name = _get_node_text(name_node, source_bytes)
            code = _get_node_text(node, source_bytes)
            
            unit = CodeUnit(
                unit_type="class",
                name=class_name,
                signature=f"class {class_name}",
                code=code,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language
            )
            
            # Extract methods within the class
            body = self._find_child_by_type(node, 'field_declaration_list')
            if body:
                self._extract_class_members(body, source_bytes, unit, language, class_name)
            
            return unit
        except Exception as e:
            self.logger.warning(f"Failed to extract class: {e}")
            return None
    
    def _extract_struct(self, node, source_bytes: bytes, language: str) -> Optional[CodeUnit]:
        """Extract a struct definition."""
        try:
            # Get struct name
            name_node = self._find_child_by_type(node, 'type_identifier')
            if not name_node:
                # Anonymous struct
                return None
            
            struct_name = _get_node_text(name_node, source_bytes)
            code = _get_node_text(node, source_bytes)
            
            unit = CodeUnit(
                unit_type="struct",
                name=struct_name,
                signature=f"struct {struct_name}",
                code=code,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language
            )
            
            # Extract members
            body = self._find_child_by_type(node, 'field_declaration_list')
            if body:
                members = self._extract_struct_members(body, source_bytes)
                unit.metadata["members"] = members
            
            return unit
        except Exception as e:
            self.logger.warning(f"Failed to extract struct: {e}")
            return None
    
    def _extract_class_members(
        self, 
        body_node, 
        source_bytes: bytes, 
        class_unit: CodeUnit,
        language: str,
        class_name: str
    ):
        """Extract methods and members from a class body."""
        for child in body_node.children:
            if child.type == 'function_definition':
                method = self._extract_function(child, source_bytes, language, class_name)
                if method:
                    class_unit.children.append(method)
            elif child.type == 'declaration':
                # Could be a method declaration or member variable
                func = self._try_extract_function_declaration(child, source_bytes, language, class_name)
                if func:
                    class_unit.children.append(func)
    
    def _extract_struct_members(self, body_node, source_bytes: bytes) -> List[Dict[str, str]]:
        """Extract struct member fields."""
        members = []
        for child in body_node.children:
            if child.type == 'field_declaration':
                member_text = _get_node_text(child, source_bytes).strip().rstrip(';')
                members.append({"declaration": member_text})
        return members
    
    def _try_extract_function_declaration(
        self, 
        node, 
        source_bytes: bytes, 
        language: str,
        class_name: Optional[str] = None
    ) -> Optional[CodeUnit]:
        """Try to extract a function declaration (prototype)."""
        try:
            declarator = self._find_descendant_by_type(node, 'function_declarator')
            if not declarator:
                return None
            
            name_node = self._find_descendant_by_type(declarator, 'identifier')
            if not name_node:
                return None
            
            func_name = _get_node_text(name_node, source_bytes)
            code = _get_node_text(node, source_bytes)
            
            # Get return type
            return_type = ""
            type_node = self._find_child_by_type(node, 'primitive_type')
            if not type_node:
                type_node = self._find_child_by_type(node, 'type_identifier')
            if type_node:
                return_type = _get_node_text(type_node, source_bytes)
            
            params = self._extract_parameters(declarator, source_bytes)
            signature = f"{return_type} {func_name}({', '.join(params)})"
            
            return CodeUnit(
                unit_type="function_declaration",
                name=func_name,
                signature=signature,
                code=code,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language,
                parent_name=class_name,
                metadata={"is_declaration": True}
            )
        except Exception:
            return None
    
    def _extract_parameters(self, declarator_node, source_bytes: bytes) -> List[str]:
        """Extract function parameters."""
        params = []
        param_list = self._find_child_by_type(declarator_node, 'parameter_list')
        if param_list:
            for child in param_list.children:
                if child.type == 'parameter_declaration':
                    param_text = _get_node_text(child, source_bytes)
                    params.append(param_text)
        return params
    
    def _extract_function_calls(self, node, source_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract function calls within a code block."""
        calls = []
        
        def traverse(n):
            if n.type == 'call_expression':
                func_node = self._find_child_by_type(n, 'identifier')
                if not func_node:
                    func_node = self._find_child_by_type(n, 'field_expression')
                
                if func_node:
                    call_name = _get_node_text(func_node, source_bytes)
                    # Clean up field expressions (obj.method -> method)
                    if '.' in call_name:
                        call_name = call_name.split('.')[-1]
                    if '->' in call_name:
                        call_name = call_name.split('->')[-1]
                    
                    calls.append({
                        "name": call_name,
                        "line": n.start_point[0] + 1
                    })
            
            for child in n.children:
                traverse(child)
        
        traverse(node)
        return calls
    
    def _find_child_by_type(self, node, type_name: str):
        """Find first direct child with given type."""
        for child in node.children:
            if child.type == type_name:
                return child
        return None
    
    def _find_descendant_by_type(self, node, type_name: str):
        """Find first descendant with given type (recursive)."""
        for child in node.children:
            if child.type == type_name:
                return child
            result = self._find_descendant_by_type(child, type_name)
            if result:
                return result
        return None
    
    def parse_directory(
        self, 
        directory: str, 
        recursive: bool = True
    ) -> List[CodeUnit]:
        """
        Parse all C/C++ files in a directory.
        
        Args:
            directory: Path to directory
            recursive: Whether to search subdirectories
            
        Returns:
            List of CodeUnit objects for each file
        """
        file_units = []
        dir_path = Path(directory)
        
        if recursive:
            files = dir_path.rglob('*')
        else:
            files = dir_path.glob('*')
        
        for file_path in files:
            if file_path.is_file() and self.is_supported_file(str(file_path)):
                try:
                    unit = self.parse_file(str(file_path))
                    file_units.append(unit)
                    self.logger.info(f"Parsed {file_path.name}: {len(unit.children)} units")
                except Exception as e:
                    self.logger.error(f"Failed to parse {file_path}: {e}")
        
        return file_units
    
    def flatten_units(self, file_unit: CodeUnit) -> List[CodeUnit]:
        """
        Flatten a file unit into a list of all code units.
        Returns file, classes, structs, functions in order.
        """
        units = [file_unit]
        
        def collect(unit: CodeUnit):
            for child in unit.children:
                units.append(child)
                collect(child)
        
        collect(file_unit)
        return units
    
    def build_call_graph(
        self, 
        file_units: List[CodeUnit]
    ) -> List[Dict[str, Any]]:
        """
        Build call graph from parsed file units.
        
        Returns:
            List of call relationships with caller/callee info
        """
        # Build name -> unit mapping
        name_to_unit: Dict[str, CodeUnit] = {}
        for file_unit in file_units:
            for unit in self.flatten_units(file_unit):
                if unit.unit_type in ['function', 'method']:
                    name_to_unit[unit.name] = unit
        
        # Build call graph
        call_graph = []
        for file_unit in file_units:
            for unit in self.flatten_units(file_unit):
                if unit.unit_type in ['function', 'method']:
                    for call in unit.function_calls:
                        callee = name_to_unit.get(call['name'])
                        call_graph.append({
                            "caller_name": unit.name,
                            "caller_file": file_unit.name,
                            "callee_name": call['name'],
                            "callee_resolved": callee is not None,
                            "call_line": call['line']
                        })
        
        return call_graph
