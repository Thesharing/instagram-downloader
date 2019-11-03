class CookieReader:

    @staticmethod
    def from_local_file(file_path, encoding='utf-8', assigner='=', separator=';'):
        with open(file_path, 'r', encoding=encoding) as f:
            return {key: value for key, value in
                    (line.strip().split(assigner, 1) for line in f.readline().split(separator))}
