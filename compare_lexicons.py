import argparse

def load_words(file_path):
    """Load words from a text file, ignoring comments and blank lines."""
    with open(file_path, 'r', encoding='utf-8') as f:
        words = {line.strip().lower() for line in f if line.strip() and not line.startswith(';')}
    return words

def compare_lexicons(file1, file2, save=False):
    """Compare two text files and print words unique to each."""
    words1 = load_words(file1)
    words2 = load_words(file2)

    only_in_1 = sorted(words1 - words2)
    only_in_2 = sorted(words2 - words1)

    print(f"\n✅ Palabras únicas en {file1}: ({len(only_in_1)})")
    print("-" * 50)
    print("\n".join(only_in_1[:50]))  # Muestra solo las primeras 50 para no saturar

    print(f"\n✅ Palabras únicas en {file2}: ({len(only_in_2)})")
    print("-" * 50)
    print("\n".join(only_in_2[:50]))

    if save:
        out1 = f"{file1}_unique.txt"
        out2 = f"{file2}_unique.txt"
        with open(out1, 'w', encoding='utf-8') as f1, open(out2, 'w', encoding='utf-8') as f2:
            f1.write("\n".join(only_in_1))
            f2.write("\n".join(only_in_2))
        print(f"\n💾 Resultados guardados en:\n- {out1}\n- {out2}")

if __name__ == "__main__":
    #parser = argparse.ArgumentParser(description="Compara dos archivos .txt de palabras.")
    #parser.add_argument("file1", help="Ruta del primer archivo .txt")
    #parser.add_argument("file2", help="Ruta del segundo archivo .txt")
    #parser.add_argument("--save", action="store_true", help="Guardar los resultados en archivos .txt")
    #args = parser.parse_args()

    compare_lexicons("lexicons\\boosters.txt", "lexicons\\booster_words.txt", save=True)
