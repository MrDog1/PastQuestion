import json
import re
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
Path('logs').mkdir(exist_ok=True)
log_filename = f"logs/dictionary_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DictionaryUpdater:
    def __init__(self, original_dict_path='final_output/disease_dictionary_v2.jsonl'):
        self.original_dict_path = original_dict_path
        self.dictionary = self.load_dictionary()
        self.new_entries_added = 0
        self.existing_updated = 0
        
    def load_dictionary(self):
        """Load existing dictionary"""
        dictionary = {}
        with open(self.original_dict_path, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                canonical = entry['canonical_ja']
                dictionary[canonical] = entry
        logger.info(f"Loaded {len(dictionary)} existing entries")
        return dictionary
    
    def update_from_new_words(self, new_words_path='new_words.jsonl'):
        """Update dictionary with entries from new words file"""
        logger.info(f"Updating dictionary from: {new_words_path}")
        
        new_entries = []
        with open(new_words_path, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                new_entries.append(entry)
        
        logger.info(f"Found {len(new_entries)} potential new entries")
        
        # Process each new entry
        for entry in new_entries:
            canonical = entry['canonical_ja']
            
            if canonical in self.dictionary:
                # Update existing entry
                self.update_existing_entry(canonical, entry)
            else:
                # Add new entry
                self.add_new_entry(entry)
        
        logger.info(f"Added {self.new_entries_added} new entries")
        logger.info(f"Updated {self.existing_updated} existing entries")
    
    def update_existing_entry(self, canonical, new_entry):
        """Update an existing dictionary entry"""
        existing = self.dictionary[canonical]
        
        # Update frequency if higher
        if new_entry['frequency'] > existing.get('frequency', 0):
            existing['frequency'] = new_entry['frequency']
            logger.info(f"Updated frequency for '{canonical}': {new_entry['frequency']}")
            self.existing_updated += 1
        
        # Add new synonyms if not already present
        existing_synonyms = set(existing.get('synonyms', []))
        new_synonyms = set(new_entry.get('synonyms', []))
        
        added_synonyms = new_synonyms - existing_synonyms
        if added_synonyms:
            existing['synonyms'].extend(list(added_synonyms))
            logger.info(f"Added synonyms to '{canonical}': {added_synonyms}")
            if canonical not in [entry['canonical_ja'] for entry in [new_entry] if self.existing_updated == 0]:
                self.existing_updated += 1
    
    def add_new_entry(self, entry):
        """Add a new entry to the dictionary"""
        canonical = entry['canonical_ja']
        
        # Create a proper dictionary entry
        dict_entry = {
            "canonical_ja": canonical,
            "canonical_en": entry.get('canonical_en', ''),
            "category": entry.get('category', 'Disease'),
            "synonyms": entry.get('synonyms', [canonical]),
            "regex": entry.get('regex', re.escape(canonical)),
            "frequency": entry.get('frequency', 1),
            "variations_merged": 0,
            "status": "newly_added",
            "added_date": datetime.now().isoformat()
        }
        
        self.dictionary[canonical] = dict_entry
        self.new_entries_added += 1
        logger.info(f"Added new entry: '{canonical}' (freq: {dict_entry['frequency']})")
    
    def save_updated_dictionary(self, output_path=None):
        """Save the updated dictionary"""
        if output_path is None:
            # Create new version number
            base_path = self.original_dict_path.replace('.jsonl', '')
            if 'v2' in base_path:
                output_path = base_path.replace('v2', 'v3') + '.jsonl'
            elif 'v3' in base_path:
                output_path = base_path.replace('v3', 'v4') + '.jsonl'
            else:
                output_path = base_path + '_updated.jsonl'
        
        # Sort entries by frequency
        sorted_entries = sorted(
            self.dictionary.values(),
            key=lambda x: x.get('frequency', 0),
            reverse=True
        )
        
        # Save as JSON Lines
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in sorted_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved updated dictionary with {len(sorted_entries)} entries to: {output_path}")
        
        # Generate summary
        self.generate_update_summary(output_path)
        
        return output_path
    
    def generate_update_summary(self, output_path):
        """Generate a summary of the update"""
        summary = {
            "update_date": datetime.now().isoformat(),
            "original_dictionary": self.original_dict_path,
            "updated_dictionary": output_path,
            "new_entries_added": self.new_entries_added,
            "existing_entries_updated": self.existing_updated,
            "total_entries": len(self.dictionary),
            "top_new_entries": []
        }
        
        # Get top new entries by frequency
        new_entries = [
            entry for entry in self.dictionary.values() 
            if entry.get('status') == 'newly_added'
        ]
        new_entries.sort(key=lambda x: x.get('frequency', 0), reverse=True)
        
        summary["top_new_entries"] = [
            {
                "canonical_ja": entry['canonical_ja'],
                "frequency": entry['frequency'],
                "synonyms_count": len(entry.get('synonyms', []))
            }
            for entry in new_entries[:10]
        ]
        
        # Save summary
        summary_path = 'dictionary_update_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Update summary saved to: {summary_path}")
        
        return summary

def main():
    logger.info("="*60)
    logger.info("DICTIONARY UPDATE TOOL")
    logger.info("="*60)
    
    updater = DictionaryUpdater()
    
    # Update from new words
    try:
        updater.update_from_new_words()
        
        # Save updated dictionary
        output_path = updater.save_updated_dictionary()
        
        print(f"\n📚 Dictionary Update Complete!")
        print(f"New entries added: {updater.new_entries_added}")
        print(f"Existing entries updated: {updater.existing_updated}")
        print(f"Total entries: {len(updater.dictionary)}")
        print(f"Updated dictionary saved to: {output_path}")
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        print("\n❌ Update failed: new_words.jsonl not found")
        print("Run coverage_analyzer.py first to generate new words file")
    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()