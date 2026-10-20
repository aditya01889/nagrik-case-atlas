from .import_csv import import_dir
import sys
print(import_dir(sys.argv[1] if len(sys.argv)>1 else 'data/import_templates'))
