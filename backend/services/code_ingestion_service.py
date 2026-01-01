"""
Code ingestion service for C/C++ source files.
Handles AST parsing, LLM summary generation, and vector storage.
"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog
from sqlalchemy.orm import Session

from core.database import Document, DataSource, CodeUnit as CodeUnitModel, CodeCallGraph
from core.config import get_settings
from services.code_parser_service import CodeParserService, CodeUnit
from services.vector_service import VectorService
from services.ollama_service import OllamaService

logger = structlog.get_logger()
settings = get_settings()


class CodeIngestionService:
    """
    Service for ingesting C/C++ code with AST-based chunking and LLM summaries.
    
    Pipeline:
    1. Parse files with tree-sitter
    2. Extract functions, classes, structs
    3. Generate hierarchical summaries (function -> class -> file)
    4. Create embeddings with code + summary
    5. Store in vector database with rich metadata
    """
    
    def __init__(self):
        self.parser = CodeParserService()
        self.vector_service = VectorService()
        self.ollama_service = OllamaService()
        self.logger = structlog.get_logger()
    
    async def ingest_code_directory(
        self,
        directory: str,
        workspace_id: int,
        data_source_id: int,
        db: Session,
        recursive: bool = True,
        max_depth: Optional[int] = None,
        include_headers: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest all C/C++ files from a directory.
        
        Args:
            directory: Path to code directory
            workspace_id: Workspace ID for isolation
            data_source_id: Data source ID
            db: Database session
            recursive: Search subdirectories
            max_depth: Maximum directory depth to scan (None = unlimited)
            include_headers: Include header files (.h, .hpp, etc.)
            
        Returns:
            Ingestion statistics
        """
        stats = {
            "files_processed": 0,
            "functions_extracted": 0,
            "classes_extracted": 0,
            "structs_extracted": 0,
            "summaries_generated": 0,
            "embeddings_created": 0,
            "errors": []
        }
        
        try:
            # Parse all files
            self.logger.info(f"Parsing C/C++ files in {directory} (max_depth={max_depth}, include_headers={include_headers})")
            file_units = self.parser.parse_directory(
                directory, 
                recursive, 
                max_depth=max_depth,
                include_headers=include_headers
            )
            stats["files_processed"] = len(file_units)
            
            if not file_units:
                self.logger.warning(f"No C/C++ files found in {directory}")
                return stats
            
            # Process each file
            all_code_units = []
            for file_unit in file_units:
                try:
                    # Create document record
                    document = Document(
                        data_source_id=data_source_id,
                        title=file_unit.name,
                        content=file_unit.code,
                        file_path=file_unit.metadata.get("file_path", ""),
                        file_type=file_unit.language,
                        doc_metadata={
                            "language": file_unit.language,
                            "includes": file_unit.includes,
                            "line_count": file_unit.end_line
                        }
                    )
                    db.add(document)
                    db.flush()
                    
                    # Process code units hierarchically
                    processed_units = await self._process_file_units(
                        file_unit, document.id, workspace_id, db, stats
                    )
                    all_code_units.extend(processed_units)
                    
                except Exception as e:
                    self.logger.error(f"Error processing file {file_unit.name}: {e}")
                    stats["errors"].append(f"{file_unit.name}: {str(e)}")
            
            # Build and store call graph
            self.logger.info("Building call graph...")
            call_graph = self.parser.build_call_graph(file_units)
            await self._store_call_graph(call_graph, all_code_units, db)
            
            # Create embeddings for all units
            self.logger.info(f"Creating embeddings for {len(all_code_units)} code units...")
            await self._create_embeddings(all_code_units, workspace_id)
            stats["embeddings_created"] = len(all_code_units)
            
            db.commit()
            self.logger.info(f"Code ingestion complete: {stats}")
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Code ingestion failed: {e}")
            stats["errors"].append(str(e))
            raise
        
        return stats
    
    async def _process_file_units(
        self,
        file_unit: CodeUnit,
        document_id: int,
        workspace_id: int,
        db: Session,
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process all code units in a file hierarchically.
        Generates summaries bottom-up: functions -> classes -> file
        """
        processed_units = []
        
        # First pass: Process functions and methods (leaf nodes)
        function_summaries = {}
        for child in file_unit.children:
            if child.unit_type in ['function', 'method', 'function_declaration']:
                stats["functions_extracted"] += 1
                summary = await self._generate_function_summary(child)
                function_summaries[child.name] = summary
                
                unit_record = self._create_code_unit_record(
                    child, document_id, None, summary, db
                )
                processed_units.append({
                    "db_id": unit_record.id,
                    "unit": child,
                    "summary": summary,
                    "document_id": document_id,
                    "workspace_id": workspace_id
                })
                stats["summaries_generated"] += 1
            
            elif child.unit_type == 'class':
                stats["classes_extracted"] += 1
                # Process class methods first
                method_summaries = {}
                for method in child.children:
                    if method.unit_type in ['method', 'function', 'function_declaration']:
                        stats["functions_extracted"] += 1
                        summary = await self._generate_function_summary(method)
                        method_summaries[method.name] = summary
                        function_summaries[method.name] = summary
                
                # Generate class summary using method summaries
                class_summary = await self._generate_class_summary(child, method_summaries)
                
                class_record = self._create_code_unit_record(
                    child, document_id, None, class_summary, db
                )
                processed_units.append({
                    "db_id": class_record.id,
                    "unit": child,
                    "summary": class_summary,
                    "document_id": document_id,
                    "workspace_id": workspace_id
                })
                stats["summaries_generated"] += 1
                
                # Store methods with parent reference
                for method in child.children:
                    if method.unit_type in ['method', 'function', 'function_declaration']:
                        method_record = self._create_code_unit_record(
                            method, document_id, class_record.id, 
                            method_summaries.get(method.name, ""), db
                        )
                        processed_units.append({
                            "db_id": method_record.id,
                            "unit": method,
                            "summary": method_summaries.get(method.name, ""),
                            "document_id": document_id,
                            "workspace_id": workspace_id
                        })
                        stats["summaries_generated"] += 1
            
            elif child.unit_type == 'struct':
                stats["structs_extracted"] += 1
                struct_summary = await self._generate_struct_summary(child)
                
                struct_record = self._create_code_unit_record(
                    child, document_id, None, struct_summary, db
                )
                processed_units.append({
                    "db_id": struct_record.id,
                    "unit": child,
                    "summary": struct_summary,
                    "document_id": document_id,
                    "workspace_id": workspace_id
                })
                stats["summaries_generated"] += 1
        
        # Generate file-level summary using all child summaries
        file_summary = await self._generate_file_summary(file_unit, function_summaries)
        
        file_record = self._create_code_unit_record(
            file_unit, document_id, None, file_summary, db
        )
        processed_units.append({
            "db_id": file_record.id,
            "unit": file_unit,
            "summary": file_summary,
            "document_id": document_id,
            "workspace_id": workspace_id
        })
        stats["summaries_generated"] += 1
        
        return processed_units
    
    def _create_code_unit_record(
        self,
        unit: CodeUnit,
        document_id: int,
        parent_id: Optional[int],
        summary: str,
        db: Session
    ) -> CodeUnitModel:
        """Create a database record for a code unit."""
        record = CodeUnitModel(
            document_id=document_id,
            unit_type=unit.unit_type,
            name=unit.name,
            signature=unit.signature,
            code=unit.code,
            summary=summary,
            start_line=unit.start_line,
            end_line=unit.end_line,
            parent_id=parent_id,
            language=unit.language,
            unit_metadata={
                "function_calls": [c["name"] for c in unit.function_calls],
                "includes": unit.includes,
                **unit.metadata
            }
        )
        db.add(record)
        db.flush()
        return record
    
    async def _generate_function_summary(self, unit: CodeUnit) -> str:
        """Generate LLM summary for a function."""
        prompt = f"""Analyze this {unit.language.upper()} function and provide a concise summary (2-3 sentences) of what it does.
Focus on: purpose, inputs, outputs, and key operations.

Function signature: {unit.signature or unit.name}

Code:
```{unit.language}
{unit.code[:2000]}  # Truncate very long functions
```

Summary:"""
        
        try:
            llm = self.ollama_service.get_llm(temperature=0.3)
            response = await asyncio.to_thread(llm.invoke, prompt)
            return response.strip()
        except Exception as e:
            self.logger.warning(f"Failed to generate summary for {unit.name}: {e}")
            return f"Function {unit.name}"
    
    async def _generate_class_summary(
        self, 
        unit: CodeUnit, 
        method_summaries: Dict[str, str]
    ) -> str:
        """Generate LLM summary for a class using method summaries."""
        methods_text = "\n".join([
            f"- {name}: {summary}" 
            for name, summary in method_summaries.items()
        ])
        
        prompt = f"""Analyze this {unit.language.upper()} class and provide a concise summary (3-4 sentences) of its purpose and functionality.

Class: {unit.name}

Method summaries:
{methods_text}

Class declaration:
```{unit.language}
{unit.code[:1500]}
```

Summary:"""
        
        try:
            llm = self.ollama_service.get_llm(temperature=0.3)
            response = await asyncio.to_thread(llm.invoke, prompt)
            return response.strip()
        except Exception as e:
            self.logger.warning(f"Failed to generate summary for class {unit.name}: {e}")
            return f"Class {unit.name} with {len(method_summaries)} methods"
    
    async def _generate_struct_summary(self, unit: CodeUnit) -> str:
        """Generate LLM summary for a struct."""
        members = unit.metadata.get("members", [])
        members_text = "\n".join([m.get("declaration", "") for m in members])
        
        prompt = f"""Analyze this {unit.language.upper()} struct and provide a concise summary (1-2 sentences) of its purpose.

Struct: {unit.name}

Members:
{members_text}

Summary:"""
        
        try:
            llm = self.ollama_service.get_llm(temperature=0.3)
            response = await asyncio.to_thread(llm.invoke, prompt)
            return response.strip()
        except Exception as e:
            self.logger.warning(f"Failed to generate summary for struct {unit.name}: {e}")
            return f"Struct {unit.name}"
    
    async def _generate_file_summary(
        self, 
        file_unit: CodeUnit, 
        function_summaries: Dict[str, str]
    ) -> str:
        """Generate LLM summary for a file using function/class summaries."""
        summaries_text = "\n".join([
            f"- {name}: {summary}" 
            for name, summary in list(function_summaries.items())[:20]  # Limit for context
        ])
        
        includes_text = ", ".join(file_unit.includes[:10]) if file_unit.includes else "None"
        
        prompt = f"""Analyze this {file_unit.language.upper()} source file and provide a concise summary (3-4 sentences) of its overall purpose.

File: {file_unit.name}
Includes: {includes_text}

Functions/Classes in this file:
{summaries_text}

Summary:"""
        
        try:
            llm = self.ollama_service.get_llm(temperature=0.3)
            response = await asyncio.to_thread(llm.invoke, prompt)
            return response.strip()
        except Exception as e:
            self.logger.warning(f"Failed to generate summary for file {file_unit.name}: {e}")
            return f"Source file {file_unit.name} with {len(function_summaries)} functions"
    
    async def _store_call_graph(
        self,
        call_graph: List[Dict[str, Any]],
        processed_units: List[Dict[str, Any]],
        db: Session
    ):
        """Store call graph relationships in database."""
        # Build name -> db_id mapping
        name_to_id = {}
        for pu in processed_units:
            if pu["unit"].unit_type in ['function', 'method']:
                name_to_id[pu["unit"].name] = pu["db_id"]
        
        for call in call_graph:
            caller_id = name_to_id.get(call["caller_name"])
            callee_id = name_to_id.get(call["callee_name"])
            
            if caller_id:
                call_record = CodeCallGraph(
                    caller_id=caller_id,
                    callee_name=call["callee_name"],
                    callee_id=callee_id,
                    call_line=call.get("call_line")
                )
                db.add(call_record)
    
    async def _create_embeddings(
        self,
        processed_units: List[Dict[str, Any]],
        workspace_id: int
    ):
        """Create vector embeddings for all code units."""
        documents = []
        
        for pu in processed_units:
            unit = pu["unit"]
            summary = pu["summary"]
            
            # Combine summary + signature + code snippet for embedding
            code_snippet = unit.code[:500] if len(unit.code) > 500 else unit.code
            
            embedding_text = f"""
{summary}

{unit.signature or unit.name}

{code_snippet}
""".strip()
            
            documents.append({
                "id": f"code_{pu['db_id']}",
                "content": embedding_text,
                "title": f"{unit.unit_type}: {unit.name}",
                "source": unit.metadata.get("file_path", unit.name),
                "workspace_id": workspace_id,
                "document_id": pu["document_id"],
                "code_unit_id": pu["db_id"],
                "unit_type": unit.unit_type,
                "start_line": unit.start_line,
                "end_line": unit.end_line,
                "language": unit.language,
                "summary": summary,
                "signature": unit.signature
            })
        
        if documents:
            await self.vector_service.add_documents(documents)
    
    async def ingest_code_files(
        self,
        files: List[Dict[str, str]],
        workspace_id: int,
        data_source_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Ingest specific code files (for uploaded files).
        
        Args:
            files: List of {"path": str, "content": str}
            workspace_id: Workspace ID
            data_source_id: Data source ID
            db: Database session
            
        Returns:
            Ingestion statistics
        """
        stats = {
            "files_processed": 0,
            "functions_extracted": 0,
            "classes_extracted": 0,
            "structs_extracted": 0,
            "summaries_generated": 0,
            "embeddings_created": 0,
            "errors": []
        }
        
        all_code_units = []
        file_units = []
        
        for file_info in files:
            file_path = file_info["path"]
            content = file_info["content"]
            
            if not self.parser.is_supported_file(file_path):
                continue
            
            try:
                file_unit = self.parser.parse_file(file_path, content)
                file_units.append(file_unit)
                stats["files_processed"] += 1
                
                # Create document record
                document = Document(
                    data_source_id=data_source_id,
                    title=file_unit.name,
                    content=content,
                    file_path=file_path,
                    file_type=file_unit.language,
                    doc_metadata={
                        "language": file_unit.language,
                        "includes": file_unit.includes
                    }
                )
                db.add(document)
                db.flush()
                
                # Process code units
                processed = await self._process_file_units(
                    file_unit, document.id, workspace_id, db, stats
                )
                all_code_units.extend(processed)
                
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                stats["errors"].append(f"{file_path}: {str(e)}")
        
        # Build call graph
        if file_units:
            call_graph = self.parser.build_call_graph(file_units)
            await self._store_call_graph(call_graph, all_code_units, db)
        
        # Create embeddings
        if all_code_units:
            await self._create_embeddings(all_code_units, workspace_id)
            stats["embeddings_created"] = len(all_code_units)
        
        db.commit()
        return stats
