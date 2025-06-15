import pandas as pd
import json
import re
import unicodedata
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Setup logging
Path('logs').mkdir(exist_ok=True)
log_filename = f"logs/coverage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DictionaryCoverageAnalyzer:
    def __init__(self, dictionary_path='final_output/disease_dictionary_v2.jsonl'):
        self.dictionary = self.load_dictionary(dictionary_path)
        self.coverage_stats = {}
        self.uncovered_terms = []
        self.new_terms = defaultdict(int)
        
    def load_dictionary(self, dict_path):
        """Load disease dictionary from JSONL file"""
        dictionary = {}
        patterns = []
        
        logger.info(f"Loading dictionary from: {dict_path}")
        
        with open(dict_path, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                canonical = entry['canonical_ja']
                dictionary[canonical] = entry
                
                # Create regex patterns for matching
                patterns.append({
                    'canonical': canonical,
                    'regex': entry.get('regex', re.escape(canonical)),
                    'synonyms': entry.get('synonyms', [canonical])
                })
        
        logger.info(f"Loaded {len(dictionary)} dictionary entries")
        return {
            'entries': dictionary,
            'patterns': patterns
        }
    
    def normalize_text(self, text):
        """Apply same normalization as the main script"""
        if pd.isna(text):
            return ""
        
        text = str(text)
        
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        
        # Remove leading numbers and symbols
        text = re.sub(r'^[0-9]+[)）:：．、.\s]+', '', text)
        text = re.sub(r'^[a-zA-Z][)）:：．、.\s]+', '', text)
        
        # Remove specimen status prefix
        text = re.sub(r'^(検体適正|検体不適正)[、，,]\s*', '', text)
        text = re.sub(r'^(悪性|良性)[／/]\s*', '', text)
        
        return text.strip()
    
    def extract_disease_terms(self, text):
        """Extract all disease terms from text"""
        normalized = self.normalize_text(text)
        if not normalized:
            return []
        
        # Split by common delimiters
        terms = []
        
        # Handle gene patterns specially
        gene_pattern = r'[A-Z][A-Z0-9]+(?:::[A-Z][A-Z0-9]+)?'
        gene_matches = re.findall(gene_pattern, normalized)
        
        # Replace genes with placeholders
        temp_text = normalized
        for i, gene in enumerate(gene_matches):
            temp_text = temp_text.replace(gene, f"__GENE{i}__")
        
        # Split by delimiters
        parts = re.split(r'[／/,、，・;]', temp_text)
        
        for part in parts:
            # Restore genes
            for i, gene in enumerate(gene_matches):
                part = part.replace(f"__GENE{i}__", gene)
            
            part = part.strip()
            if part and len(part) > 1:
                # Extract main disease name (before parentheses)
                match = re.match(r'^([^（\(]+)', part)
                if match:
                    main_term = match.group(1).strip()
                    terms.append(main_term)
                    
                    # Check for gene in parentheses
                    gene_in_paren = re.search(r'[（\(](' + gene_pattern + r')[）\)]', part)
                    if gene_in_paren:
                        terms.append(f"{main_term} ({gene_in_paren.group(1)})")
                else:
                    terms.append(part)
        
        return terms
    
    def check_coverage(self, term):
        """Check if a term is covered by the dictionary"""
        # Direct match
        if term in self.dictionary['entries']:
            return True, 'exact_match'
        
        # Pattern match
        for pattern in self.dictionary['patterns']:
            # Check synonyms
            if term in pattern['synonyms']:
                return True, 'synonym_match'
            
            # Regex match
            try:
                if re.match(pattern['regex'], term, re.IGNORECASE):
                    return True, 'regex_match'
            except:
                pass
        
        # Partial match check (for compound terms)
        for entry in self.dictionary['entries'].values():
            canonical = entry['canonical_ja']
            if canonical in term or term in canonical:
                return True, 'partial_match'
        
        return False, 'not_covered'
    
    def analyze_excel_coverage(self, excel_path, sheet_name="DB疾患", column_index=3):
        """Analyze coverage of the dictionary against Excel data"""
        logger.info(f"Analyzing coverage for: {excel_path}")
        
        # Load Excel data
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        column_name = df.columns[column_index]
        
        total_entries = 0
        covered_entries = 0
        uncovered_unique = set()
        coverage_details = defaultdict(int)
        
        # Process each entry
        for idx, raw_text in enumerate(df.iloc[:, column_index]):
            if pd.isna(raw_text):
                continue
            
            # Extract disease terms
            terms = self.extract_disease_terms(raw_text)
            
            for term in terms:
                total_entries += 1
                is_covered, match_type = self.check_coverage(term)
                
                if is_covered:
                    covered_entries += 1
                    coverage_details[match_type] += 1
                else:
                    uncovered_unique.add(term)
                    self.new_terms[term] += 1
            
            # Log progress
            if (idx + 1) % 200 == 0:
                logger.info(f"Processed {idx + 1} entries...")
        
        # Calculate coverage
        coverage_percent = (covered_entries / total_entries * 100) if total_entries > 0 else 0
        
        self.coverage_stats = {
            'total_terms': total_entries,
            'covered_terms': covered_entries,
            'uncovered_terms': total_entries - covered_entries,
            'coverage_percent': coverage_percent,
            'unique_uncovered': len(uncovered_unique),
            'match_types': dict(coverage_details)
        }
        
        self.uncovered_terms = sorted(uncovered_unique)
        
        # Log results
        logger.info("\n" + "="*60)
        logger.info("COVERAGE ANALYSIS RESULTS")
        logger.info("="*60)
        logger.info(f"Total disease terms: {total_entries}")
        logger.info(f"Covered terms: {covered_entries}")
        logger.info(f"Coverage rate: {coverage_percent:.2f}%")
        logger.info(f"Unique uncovered terms: {len(uncovered_unique)}")
        logger.info(f"\nMatch type breakdown:")
        for match_type, count in coverage_details.items():
            logger.info(f"  {match_type}: {count}")
        
        # Show top uncovered terms
        logger.info(f"\nTop 20 uncovered terms (by frequency):")
        top_uncovered = sorted(self.new_terms.items(), key=lambda x: x[1], reverse=True)[:20]
        for term, freq in top_uncovered:
            logger.info(f"  '{term}': {freq} occurrences")
        
        return self.coverage_stats
    
    def generate_new_words_file(self, output_path='new_words.jsonl'):
        """Generate a file of new words for easy addition to dictionary"""
        logger.info(f"\nGenerating new words file: {output_path}")
        
        new_entries = []
        for term in self.uncovered_terms:
            # Create a template entry
            entry = {
                "canonical_ja": term,
                "canonical_en": "",
                "category": "Disease",
                "synonyms": [term],
                "regex": re.escape(term),
                "frequency": self.new_terms[term],
                "status": "new",
                "added_date": datetime.now().isoformat()
            }
            new_entries.append(entry)
        
        # Sort by frequency
        new_entries.sort(key=lambda x: x['frequency'], reverse=True)
        
        # Save to JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in new_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(new_entries)} new words to {output_path}")
        
        # Also create a simple text file for review
        with open('new_words_list.txt', 'w', encoding='utf-8') as f:
            f.write("NEW DISEASE TERMS NOT IN DICTIONARY\n")
            f.write("="*50 + "\n")
            f.write(f"Total: {len(self.uncovered_terms)} unique terms\n")
            f.write(f"Coverage: {self.coverage_stats['coverage_percent']:.2f}%\n")
            f.write("="*50 + "\n\n")
            
            for term in sorted(self.uncovered_terms):
                f.write(f"{term} (出現回数: {self.new_terms[term]})\n")
        
        return new_entries
    
    def generate_coverage_report(self):
        """Generate comprehensive coverage report"""
        report_path = 'coverage_analysis_report.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("DICTIONARY COVERAGE ANALYSIS REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            f.write("SUMMARY\n")
            f.write("-"*30 + "\n")
            f.write(f"Dictionary entries: {len(self.dictionary['entries'])}\n")
            f.write(f"Total terms analyzed: {self.coverage_stats['total_terms']}\n")
            f.write(f"Covered terms: {self.coverage_stats['covered_terms']}\n")
            f.write(f"Coverage rate: {self.coverage_stats['coverage_percent']:.2f}%\n")
            f.write(f"Unique uncovered terms: {self.coverage_stats['unique_uncovered']}\n\n")
            
            f.write("MATCH TYPE BREAKDOWN\n")
            f.write("-"*30 + "\n")
            for match_type, count in self.coverage_stats['match_types'].items():
                f.write(f"{match_type}: {count}\n")
            
            f.write("\n\nRECOMMENDATIONS\n")
            f.write("-"*30 + "\n")
            
            if self.coverage_stats['coverage_percent'] < 95:
                f.write("⚠️ Coverage is below 95% target!\n")
                f.write("Actions needed:\n")
                f.write("1. Review new_words.jsonl and add high-frequency terms\n")
                f.write("2. Update normalization rules for common patterns\n")
                f.write("3. Add more synonyms and regex patterns\n")
            else:
                f.write("✓ Coverage exceeds 95% target!\n")
        
        logger.info(f"Coverage report saved to: {report_path}")

def main():
    logger.info("="*60)
    logger.info("DICTIONARY COVERAGE ANALYZER")
    logger.info("="*60)
    
    analyzer = DictionaryCoverageAnalyzer()
    
    # Analyze coverage
    excel_path = "専門医試験比較表.xlsx"
    stats = analyzer.analyze_excel_coverage(excel_path)
    
    # Generate new words file
    analyzer.generate_new_words_file()
    
    # Generate report
    analyzer.generate_coverage_report()
    
    print(f"\n📊 Coverage Analysis Complete!")
    print(f"Coverage Rate: {stats['coverage_percent']:.2f}%")
    print(f"{'✅' if stats['coverage_percent'] >= 95 else '⚠️'} Target: 95%")
    print(f"\nFiles generated:")
    print("  - new_words.jsonl (for dictionary updates)")
    print("  - new_words_list.txt (for manual review)")
    print("  - coverage_analysis_report.txt (detailed report)")
    print(f"  - logs/coverage_analysis_*.log")

if __name__ == "__main__":
    main()