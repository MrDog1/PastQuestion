# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese medical examination database project focused on normalizing disease names in specialist exam past questions (過去問). The project achieves 95.56% coverage in disease name normalization.

## Key Files and Directories

### Data Files
- `専門医試験比較表.xlsx` - Source Excel file with disease names in column D of "DB疾患" sheet
- `専門医試験DB How to.docx` - Specification document for normalization rules

### Main Scripts (final_output/)
- `normalize_diseases_v3.py` - Main normalization script using v3 dictionary
- `disease_dictionary_v3.jsonl` - Disease dictionary with 812 entries (95.56% coverage)

### Tools (tools/)
- `coverage_analyzer.py` - Analyzes dictionary coverage and generates new word reports
- `update_dictionary.py` - Updates dictionary with new terms
- `dictionary_maintenance_tool.py` - CLI tool for dictionary maintenance

## Key Achievements
- Reduced unique disease names from 913 to 784 (14.1% reduction)
- Achieved 95.56% dictionary coverage
- Properly handles gene names (C3, MLH1, ETV6::NTRK3)
- Merges variations like "2）腺癌" → "腺癌"

## Common Commands
```bash
# Run normalization
cd final_output && python normalize_diseases_v3.py

# Check coverage
python tools/coverage_analyzer.py

# Dictionary maintenance
python tools/dictionary_maintenance_tool.py stats
```

## Important Notes
- Disease names may contain prefixes like "1)", "a:" which need removal
- Gene names should be preserved in uppercase
- Specimen status terms (陰性、陽性、検体適正) should be removed
- The project uses JSON Lines format for the dictionary

## Git Version Control
**IMPORTANT**: Always use Git to track changes appropriately:

### When to Commit
- After implementing new features or fixes
- After updating the dictionary
- After running coverage analysis with significant improvements
- Before making major changes to existing code

### Commit Guidelines
```bash
# Check status before committing
git status

# Add and commit with descriptive message
git add -A
git commit -m "Clear description of changes"

# Example commit messages:
# "Update dictionary to 96% coverage with 20 new disease terms"
# "Add batch processing feature to normalization script"
# "Fix gene name handling in dictionary update tool"
```

### What to Track
- ✅ Source code changes (*.py)
- ✅ Dictionary updates (*.jsonl)
- ✅ Documentation updates (*.md)
- ✅ Important reports (coverage analysis)
- ❌ Temporary files (logs/, temp_files/)
- ❌ Large generated files (use .gitignore)

### Branch Strategy
- `main` - Stable, tested code
- Create feature branches for major changes
- Test thoroughly before merging to main