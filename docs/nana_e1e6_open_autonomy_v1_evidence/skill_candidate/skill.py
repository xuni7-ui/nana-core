def transform(data):
    return sum(x for x in data if isinstance(x, (int, float)))
