import os

class Storage:
    def __init__(self, base_dir='results'):
        print(f"[storage.py] Storage initialized with base_dir={base_dir}")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_report(self, query, report):
        filename = os.path.join(self.base_dir, f"{hash(query)}.txt")
        print(f"[storage.py] Saving report to {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
