import pandas as pd
import re
import json
import unicodedata
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Setup logging
Path('logs').mkdir(exist_ok=True)
log_filename = f"logs/normalization_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImprovedDiseaseNormalizer:
    def __init__(self, dictionary_path='disease_dictionary_v3.jsonl'):
        self.disease_dict = self.load_dictionary(dictionary_path)
        self.normalization_map = defaultdict(list)
        self.gene_patterns = set()
        self.specimen_terms = {
            '陰性', '陽性', '検体適正', '検体不適正', 'NILM', 'ASC-US', 'ASC-H',
            'R0', 'R1', 'R2', '良性', '正常', '異常なし', '悪性'
        }
        
    def load_dictionary(self, dict_path):
        """Load disease dictionary for better normalization"""
        dictionary = {}
        if Path(dict_path).exists():
            logger.info(f"Loading dictionary from: {dict_path}")
            with open(dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    canonical = entry['canonical_ja']
                    dictionary[canonical] = entry
            logger.info(f"Loaded {len(dictionary)} dictionary entries")
        return dictionary
        
    def is_gene_name(self, text):
        """Check if text is likely a gene name"""
        # Gene patterns: MLH1, ETV6::NTRK3, C3, MYC, etc.
        gene_pattern = r'^[A-Z][A-Z0-9]{1,}(?:::[A-Z][A-Z0-9]+)?$'
        return bool(re.match(gene_pattern, text))
    
    def preprocess_text(self, text):
        """Apply preprocessing steps according to the How-to document"""
        if pd.isna(text):
            return ""
        
        text = str(text)
        original_text = text
        
        # 1. Unicode normalization (NFKC)
        text = unicodedata.normalize('NFKC', text)
        
        # 2. Remove leading numbers and symbols
        text = re.sub(r'^[0-9]+[)）:：．、.\s]+', '', text)
        text = re.sub(r'^[a-zA-Z][)）:：．、.\s]+', '', text)
        
        logger.debug(f"Preprocessed: '{original_text}' → '{text}'")
        return text.strip()
    
    def extract_main_disease(self, text):
        """Extract the main disease name from text"""
        # Handle patterns like "検体適正、悪性／浸潤性乳管癌"
        if '検体適正' in text or '検体不適正' in text:
            # Remove specimen status part
            text = re.sub(r'^[^、，,]+[、，,]\s*', '', text)
        
        # Remove "悪性／" or "良性／" prefixes
        text = re.sub(r'^(悪性|良性)[／/]\s*', '', text)
        
        # Extract main disease before parentheses
        match = re.match(r'^([^（\(]+)', text)
        if match:
            main_disease = match.group(1).strip()
            
            # Handle cases with gene names in parentheses
            paren_match = re.search(r'[（\(]([A-Z0-9]+(?:::[A-Z0-9]+)?)[）\)]', text)
            if paren_match and self.is_gene_name(paren_match.group(1)):
                # Keep gene name with disease
                return f"{main_disease} ({paren_match.group(1)})"
            else:
                return main_disease
        
        return text
    
    def normalize_disease_name(self, disease):
        """Apply normalization rules to disease name"""
        # Standardize cancer terms
        disease = re.sub(r'がん$', '癌', disease)
        disease = re.sub(r'ガン$', '癌', disease)
        
        # Standardize spaces
        disease = re.sub(r'\s+', ' ', disease).strip()
        
        # Keep gene names in uppercase
        def preserve_gene_case(match):
            gene = match.group(0)
            if self.is_gene_name(gene):
                return gene
            else:
                return gene
        
        # Find and preserve gene names
        disease = re.sub(r'\b[A-Z][A-Z0-9]+(?:::[A-Z][A-Z0-9]+)?\b', preserve_gene_case, disease)
        
        return disease
    
    def process_entry(self, raw_text):
        """Process a single entry and return normalized disease name(s)"""
        if pd.isna(raw_text):
            return ""
        
        # Preprocess
        text = self.preprocess_text(raw_text)
        
        # Handle multiple diseases separated by various delimiters
        # But be careful not to split gene names like "ETV6::NTRK3"
        parts = []
        
        # First split by major delimiters, but preserve gene patterns
        temp_text = text
        gene_placeholders = {}
        gene_counter = 0
        
        # Replace gene patterns with placeholders
        for match in re.finditer(r'[A-Z][A-Z0-9]+::[A-Z][A-Z0-9]+', temp_text):
            placeholder = f"__GENE{gene_counter}__"
            gene_placeholders[placeholder] = match.group(0)
            temp_text = temp_text.replace(match.group(0), placeholder)
            gene_counter += 1
        
        # Split by delimiters
        if re.search(r'[／/]', temp_text) and not re.search(r'(悪性|良性)[／/]', temp_text):
            parts = re.split(r'[／/]', temp_text)
        elif re.search(r'[,、，]', temp_text):
            parts = re.split(r'[,、，]', temp_text)
        else:
            parts = [temp_text]
        
        # Restore gene patterns
        restored_parts = []
        for part in parts:
            for placeholder, gene in gene_placeholders.items():
                part = part.replace(placeholder, gene)
            restored_parts.append(part)
        
        # Process each part
        normalized_diseases = []
        for part in restored_parts:
            part = part.strip()
            if not part or part in self.specimen_terms:
                continue
            
            # Extract main disease
            main_disease = self.extract_main_disease(part)
            
            # Normalize
            normalized = self.normalize_disease_name(main_disease)
            
            if normalized and normalized not in self.specimen_terms:
                normalized_diseases.append(normalized)
                
                # Track mapping
                if str(raw_text) != normalized:
                    self.normalization_map[normalized].append(str(raw_text))
        
        # Return single disease or multiple diseases joined
        if len(normalized_diseases) == 0:
            return str(raw_text)  # Return original if no disease found
        elif len(normalized_diseases) == 1:
            return normalized_diseases[0]
        else:
            # For multiple diseases, return the first one (main disease)
            # This helps with deduplication
            return normalized_diseases[0]
    
    def process_excel_file(self, file_path, sheet_name="DB疾患", column_index=3):
        """Process the Excel file and normalize disease names"""
        logger.info(f"Processing Excel file: {file_path}")
        logger.info(f"Target sheet: {sheet_name}, Column: {column_index}")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            column_name = df.columns[column_index]
            logger.info(f"Processing column: '{column_name}'")
            
            # Process each entry
            normalized_entries = []
            
            for idx, raw_text in enumerate(df.iloc[:, column_index]):
                normalized = self.process_entry(raw_text)
                normalized_entries.append(normalized)
                
                # Log progress
                if (idx + 1) % 100 == 0:
                    logger.info(f"Processed {idx + 1} entries...")
            
            # Add normalized column
            df[f'{column_name}_正規化'] = normalized_entries
            
            # Calculate statistics
            self.calculate_statistics(df.iloc[:, column_index], normalized_entries)
            
            # Save results
            output_path = file_path.replace('.xlsx', '_normalized_v2.xlsx')
            df.to_excel(output_path, sheet_name=sheet_name, index=False)
            logger.info(f"Saved normalized data to: {output_path}")
            
            # Save dictionary
            self.save_disease_dictionary(normalized_entries)
            
            # Save mapping report
            self.save_mapping_report()
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {e}", exc_info=True)
            raise
    
    def calculate_statistics(self, original_column, normalized_entries):
        """Calculate and log statistics"""
        # Count occurrences
        original_counts = Counter(original_column.dropna())
        normalized_counts = Counter(normalized_entries)
        
        # Calculate stats
        original_unique = len(original_counts)
        normalized_unique = len(normalized_counts)
        
        logger.info("\n" + "="*60)
        logger.info("NORMALIZATION STATISTICS")
        logger.info("="*60)
        logger.info(f"Original unique values: {original_unique}")
        logger.info(f"Normalized unique values: {normalized_unique}")
        logger.info(f"Reduction: {original_unique - normalized_unique} ({(original_unique - normalized_unique) / original_unique * 100:.1f}%)")
        
        # Top diseases after normalization
        logger.info(f"\nTop 20 most frequent diseases after normalization:")
        for disease, count in normalized_counts.most_common(20):
            logger.info(f"  {disease}: {count} occurrences")
        
        # Diseases that were merged
        logger.info(f"\nDiseases with most variations merged:")
        merge_counts = [(disease, len(variations)) for disease, variations in self.normalization_map.items()]
        merge_counts.sort(key=lambda x: x[1], reverse=True)
        
        for disease, variation_count in merge_counts[:10]:
            logger.info(f"  '{disease}': {variation_count} variations merged")
            # Show some examples
            examples = self.normalization_map[disease][:3]
            for ex in examples:
                logger.info(f"    ← '{ex}'")
    
    def save_disease_dictionary(self, normalized_entries):
        """Save disease dictionary in JSON Lines format"""
        disease_counts = Counter(normalized_entries)
        dictionary_entries = []
        
        for disease, count in disease_counts.items():
            # Collect all original forms
            synonyms = [disease]
            if disease in self.normalization_map:
                # Add unique original forms as synonyms
                for original in set(self.normalization_map[disease]):
                    if original != disease:
                        synonyms.append(original)
            
            entry = {
                "canonical_ja": disease,
                "canonical_en": "",
                "category": "Disease",
                "synonyms": synonyms[:5],  # Limit synonyms
                "regex": re.escape(disease),
                "frequency": count,
                "variations_merged": len(self.normalization_map.get(disease, []))
            }
            dictionary_entries.append(entry)
        
        # Sort by frequency
        dictionary_entries.sort(key=lambda x: x['frequency'], reverse=True)
        
        # Save as JSON Lines
        dict_path = 'disease_dictionary_v2.jsonl'
        with open(dict_path, 'w', encoding='utf-8') as f:
            for entry in dictionary_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info(f"\nSaved disease dictionary with {len(dictionary_entries)} entries to: {dict_path}")
    
    def save_mapping_report(self):
        """Save detailed mapping report"""
        report_path = 'normalization_mapping_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("Disease Normalization Mapping Report\n")
            f.write("="*60 + "\n\n")
            
            # Sort by number of variations
            sorted_mappings = sorted(
                self.normalization_map.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            for normalized, originals in sorted_mappings:
                f.write(f"\n{normalized} ({len(originals)} variations):\n")
                for original in sorted(set(originals)):
                    f.write(f"  ← {original}\n")
        
        logger.info(f"Saved mapping report to: {report_path}")

def main():
    logger.info("="*60)
    logger.info("IMPROVED DISEASE NORMALIZATION TOOL V2")
    logger.info("="*60)
    
    normalizer = ImprovedDiseaseNormalizer()
    
    excel_path = "/mnt/c/Users/IWATA/過去問処理/過去問DB/専門医試験比較表.xlsx"
    
    try:
        df = normalizer.process_excel_file(excel_path)
        logger.info("\nNormalization completed successfully!")
        
    except Exception as e:
        logger.error(f"Normalization failed: {e}")
        raise

if __name__ == "__main__":
    main()