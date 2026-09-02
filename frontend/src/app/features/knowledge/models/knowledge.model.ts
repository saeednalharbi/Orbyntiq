export interface KnowledgeStatus {
  status: string;
  collection: string;
  points_count: number;
  indexed_vectors_count: number;
  document_count: number;
  vector_size: number;
  distance: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;
  supported_file_types: readonly string[];
}

export interface KnowledgeDocument {
  document_id: string;
  file_name: string;
  source_path: string;
  checksum: string;
  chunk_count: number;
  page_count: number;
}

export interface KnowledgeDocumentsResponse {
  count: number;
  documents: readonly KnowledgeDocument[];
}

export interface KnowledgeSearchRequest {
  query: string;
  limit: number;
  score_threshold: number | null;
  document_id?: string;
  file_name?: string;
}

export interface KnowledgeSearchResult {
  id: string;
  score: number;
  document_id: string;
  chunk_index: number;
  text: string;
  source_path: string;
  file_name: string;
  checksum: string;
  page_number: number | null;
}

export interface KnowledgeSearchResponse {
  query: string;
  count: number;
  results: readonly KnowledgeSearchResult[];
}

export interface KnowledgeIngestResponse {
  document_id: string;
  file_name: string;
  checksum: string;
  chunks_indexed: number;
}

export interface KnowledgeState {
  status: KnowledgeStatus | null;
  documents: readonly KnowledgeDocument[];
  searchResults: readonly KnowledgeSearchResult[];
  searchQuery: string;
  selectedDocumentId: string | null;
  loading: boolean;
  searching: boolean;
  uploading: boolean;
  uploadProgress: number | null;
  error: string | null;
  lastIngestion: KnowledgeIngestResponse | null;
}
