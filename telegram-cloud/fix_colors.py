
import os
import re

def fix_templates():
    template_dir = r'd:\ULstorage\telegram-cloud\templates'
    
    # Direct replacements for common patterns
    replacements = {
        r'text-cyan-600': 'text-ag-cyan-600',
        r'text-cyan-700': 'text-ag-cyan-700',
        r'text-cyan-500': 'text-ag-cyan-500',
        r'text-blue-600': 'text-ag-blue-600',
        r'bg-cyan-100': 'bg-ag-cyan-100',
        r'bg-cyan-50': 'bg-ag-cyan-50',
        r'bg-blue-100': 'bg-ag-blue-100',
        r'bg-blue-50': 'bg-ag-blue-50',
        r'bg-violet-100': 'bg-ag-violet-100',
        r'bg-violet-50': 'bg-ag-violet-50',
        r'from-cyan-500': 'from-ag-cyan-500',
        r'via-blue-500': 'via-ag-blue-500',
        r'to-violet-500': 'to-ag-violet-500',
        r'focus:ring-cyan-500/50': 'focus:ring-ag-cyan-500/50',
        r'focus:border-cyan-500': 'focus:border-ag-cyan-500',
        r'hover:border-cyan-500': 'hover:border-ag-cyan-500',
        r'shadow-cyan-500/10': 'shadow-ag-cyan-500/10',
        r'border-cyan-500': 'border-ag-cyan-500',
        r'bg-cyan-600': 'bg-ag-cyan-600',
        r'bg-cyan-500': 'bg-ag-cyan-500',
        r'text-blue-900': 'text-ag-blue-900',
        r'text-blue-800': 'text-ag-blue-800',
    }

    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for old, new in replacements.items():
                    new_content = new_content.replace(old, new)
                
                if new_content != content:
                    print(f"Fixed {path}")
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

if __name__ == "__main__":
    fix_templates()
