from pathlib import Path

source = Path("russell_2000_symbols.txt")
out = Path("daily_500_symbols_batch_3.txt")

symbols = []
for line in source.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
    s = line.strip().upper()
    if s and not s.startswith("#"):
        symbols.append(s)

symbols = sorted(set(symbols))

# Batch 1/2 already covered earlier symbols.
# This takes the next 500 after the first 1000.
batch = symbols[1000:1500]

out.write_text("\n".join(batch) + "\n", encoding="utf-8")

print("Total Russell symbols:", len(symbols))
print("Batch 3 symbols:", len(batch))
print("First:", batch[:10])
print("Last:", batch[-10:])
print("Output:", out)
