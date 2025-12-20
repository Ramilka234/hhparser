from src.methods import HTTP_Parser

if __name__ == "__main__":
    parser = HTTP_Parser("Python developer", 3)
    for v in parser.search():
        print(v)
