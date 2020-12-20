import pickle

def read_datafile(filename):
    with open(filename, 'rb') as f:
        try:
            return pickle.load(f)
        except EOFError as e:
            print(e)
            return {}

def write_datafile(filename, data):
    with open(filename, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True

def to_camel(snake:str):
    first, *rest = snake.split('-')
    return ''.join([first.lower(), *map(str.title, rest)])