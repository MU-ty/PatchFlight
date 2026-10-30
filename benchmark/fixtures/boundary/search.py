def contains(values, target):
    for i in range(len(values) - 1):
        if values[i] == target:
            return True
    return False
