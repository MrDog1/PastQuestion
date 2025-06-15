#!/usr/bin/env python3
"""
Dictionary Maintenance Tool

A comprehensive CLI tool for maintaining the disease dictionary.
Provides statistics, validation, and interactive editing capabilities.
"""

import json
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

# Setup logging
Path('logs').mkdir(exist_ok=True)
log_filename = f"logs/dict_maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DictionaryMaintenanceTool:
    def __init__(self, dictionary_path='final_output/disease_dictionary_v3.jsonl'):
        self.dictionary_path = dictionary_path
        self.dictionary = self.load_dictionary()
        self.stats = {}
        
    def load_dictionary(self):
        """Load the dictionary from JSONL file"""
        dictionary = {}
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = json.loads(line)
                        canonical = entry['canonical_ja']
                        dictionary[canonical] = entry
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON error on line {line_num}: {e}")
                        continue
        except FileNotFoundError:
            logger.error(f"Dictionary file not found: {self.dictionary_path}")
            return {}
        
        logger.info(f"Loaded {len(dictionary)} dictionary entries")
        return dictionary
    
    def calculate_stats(self):
        """Calculate comprehensive dictionary statistics"""
        total_entries = len(self.dictionary)
        total_frequency = sum(entry.get('frequency', 0) for entry in self.dictionary.values())
        total_variations = sum(entry.get('variations_merged', 0) for entry in self.dictionary.values())
        
        # Category breakdown
        categories = Counter(entry.get('category', 'Unknown') for entry in self.dictionary.values())
        
        # Frequency distribution
        frequencies = [entry.get('frequency', 0) for entry in self.dictionary.values()]
        freq_ranges = {
            '1': sum(1 for f in frequencies if f == 1),
            '2-5': sum(1 for f in frequencies if 2 <= f <= 5),
            '6-10': sum(1 for f in frequencies if 6 <= f <= 10),
            '11-20': sum(1 for f in frequencies if 11 <= f <= 20),
            '20+': sum(1 for f in frequencies if f > 20)
        }
        
        # Synonym statistics
        synonym_counts = [len(entry.get('synonyms', [])) for entry in self.dictionary.values()]
        avg_synonyms = sum(synonym_counts) / len(synonym_counts) if synonym_counts else 0
        
        # Top entries by frequency
        top_by_freq = sorted(
            self.dictionary.items(),
            key=lambda x: x[1].get('frequency', 0),
            reverse=True
        )[:10]
        
        # Entries with most variations merged
        top_by_variations = sorted(
            self.dictionary.items(),
            key=lambda x: x[1].get('variations_merged', 0),
            reverse=True
        )[:10]
        
        self.stats = {
            'total_entries': total_entries,
            'total_frequency': total_frequency,
            'total_variations_merged': total_variations,
            'categories': dict(categories),
            'frequency_ranges': freq_ranges,
            'average_synonyms': round(avg_synonyms, 2),
            'top_by_frequency': [(name, data.get('frequency', 0)) for name, data in top_by_freq],
            'top_by_variations': [(name, data.get('variations_merged', 0)) for name, data in top_by_variations]
        }
        
        return self.stats
    
    def print_stats(self):
        """Print formatted statistics"""
        if not self.stats:
            self.calculate_stats()
        
        print("\n" + "="*60)
        print("🔍 DICTIONARY MAINTENANCE STATISTICS")
        print("="*60)
        
        print(f"\n📊 OVERVIEW")
        print(f"Total Entries: {self.stats['total_entries']:,}")
        print(f"Total Disease Occurrences: {self.stats['total_frequency']:,}")
        print(f"Total Variations Merged: {self.stats['total_variations_merged']:,}")
        print(f"Average Synonyms per Entry: {self.stats['average_synonyms']}")
        
        print(f"\n📂 CATEGORIES")
        for category, count in self.stats['categories'].items():
            print(f"  {category}: {count:,}")
        
        print(f"\n📈 FREQUENCY DISTRIBUTION")
        for range_name, count in self.stats['frequency_ranges'].items():
            print(f"  {range_name} occurrences: {count:,} entries")
        
        print(f"\n🔥 TOP 10 BY FREQUENCY")
        for i, (name, freq) in enumerate(self.stats['top_by_frequency'], 1):
            print(f"  {i:2d}. {name} ({freq} occurrences)")
        
        print(f"\n🔀 TOP 10 BY VARIATIONS MERGED")
        for i, (name, variations) in enumerate(self.stats['top_by_variations'], 1):
            if variations > 0:
                print(f"  {i:2d}. {name} ({variations} variations)")
    
    def validate_dictionary(self):
        """Validate dictionary entries and report issues"""
        issues = defaultdict(list)
        
        for canonical, entry in self.dictionary.items():
            # Check required fields
            required_fields = ['canonical_ja', 'category', 'synonyms', 'regex']
            for field in required_fields:
                if field not in entry:
                    issues['missing_fields'].append((canonical, field))
            
            # Check canonical_ja matches key
            if entry.get('canonical_ja') != canonical:
                issues['canonical_mismatch'].append(canonical)
            
            # Check synonyms list
            synonyms = entry.get('synonyms', [])
            if not isinstance(synonyms, list):
                issues['invalid_synonyms'].append(canonical)
            elif len(synonyms) == 0:
                issues['empty_synonyms'].append(canonical)
            
            # Check regex validity
            regex_pattern = entry.get('regex', '')
            if regex_pattern:
                try:
                    re.compile(regex_pattern)
                except re.error:
                    issues['invalid_regex'].append((canonical, regex_pattern))
            
            # Check frequency
            frequency = entry.get('frequency', 0)
            if not isinstance(frequency, int) or frequency < 0:
                issues['invalid_frequency'].append((canonical, frequency))
        
        # Print validation results
        print("\n" + "="*60)
        print("✅ DICTIONARY VALIDATION RESULTS")
        print("="*60)
        
        if not any(issues.values()):
            print("\n🎉 No issues found! Dictionary is valid.")
        else:
            total_issues = sum(len(issue_list) for issue_list in issues.values())
            print(f"\n⚠️  Found {total_issues} issues:")
            
            for issue_type, issue_list in issues.items():
                if issue_list:
                    print(f"\n{issue_type.replace('_', ' ').title()}: {len(issue_list)}")
                    for item in issue_list[:5]:  # Show first 5 examples
                        if isinstance(item, tuple):
                            print(f"  - {item[0]}: {item[1]}")
                        else:
                            print(f"  - {item}")
                    if len(issue_list) > 5:
                        print(f"  ... and {len(issue_list) - 5} more")
        
        return dict(issues)
    
    def search_entries(self, search_term):
        """Search for entries containing the search term"""
        matches = []
        search_lower = search_term.lower()
        
        for canonical, entry in self.dictionary.items():
            # Search in canonical name
            if search_lower in canonical.lower():
                matches.append((canonical, entry, 'canonical'))
                continue
            
            # Search in synonyms
            synonyms = entry.get('synonyms', [])
            for synonym in synonyms:
                if search_lower in synonym.lower():
                    matches.append((canonical, entry, f'synonym: {synonym}'))
                    break
        
        return matches
    
    def print_search_results(self, search_term):
        """Print formatted search results"""
        matches = self.search_entries(search_term)
        
        print(f"\n🔍 Search results for '{search_term}': {len(matches)} matches")
        print("-" * 60)
        
        for canonical, entry, match_type in matches[:20]:  # Limit to 20 results
            freq = entry.get('frequency', 0)
            variations = entry.get('variations_merged', 0)
            print(f"\n📌 {canonical}")
            print(f"   Frequency: {freq}, Variations: {variations}")
            print(f"   Match: {match_type}")
            
            synonyms = entry.get('synonyms', [])
            if len(synonyms) > 1:
                print(f"   Synonyms: {', '.join(synonyms[1:3])}{'...' if len(synonyms) > 3 else ''}")
        
        if len(matches) > 20:
            print(f"\n... and {len(matches) - 20} more matches")
    
    def backup_dictionary(self):
        """Create a backup of the current dictionary"""
        backup_dir = Path('dictionary_backups')
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"dictionary_backup_{timestamp}.jsonl"
        
        # Copy current dictionary
        with open(self.dictionary_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        print(f"\n💾 Dictionary backed up to: {backup_path}")
        return backup_path

def main():
    parser = argparse.ArgumentParser(
        description="Dictionary Maintenance Tool for Disease Name Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dictionary_maintenance_tool.py stats
  python dictionary_maintenance_tool.py validate
  python dictionary_maintenance_tool.py search "腺癌"
  python dictionary_maintenance_tool.py backup
        """
    )
    
    parser.add_argument(
        'command',
        choices=['stats', 'validate', 'search', 'backup'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'search_term',
        nargs='?',
        help='Search term (required for search command)'
    )
    
    parser.add_argument(
        '--dict-path',
        default='final_output/disease_dictionary_v3.jsonl',
        help='Path to dictionary file'
    )
    
    args = parser.parse_args()
    
    # Initialize tool
    tool = DictionaryMaintenanceTool(args.dict_path)
    
    if not tool.dictionary:
        print(f"❌ Failed to load dictionary from {args.dict_path}")
        return 1
    
    # Execute command
    if args.command == 'stats':
        tool.print_stats()
    
    elif args.command == 'validate':
        tool.validate_dictionary()
    
    elif args.command == 'search':
        if not args.search_term:
            print("❌ Search term required for search command")
            return 1
        tool.print_search_results(args.search_term)
    
    elif args.command == 'backup':
        tool.backup_dictionary()
    
    return 0

if __name__ == "__main__":
    exit(main())