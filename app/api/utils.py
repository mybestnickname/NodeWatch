import importlib.machinery
import inspect
import os


def find_check_subclasses(directory: str, base_class: type):
    check_classes = set()

    # Рекурсивно обходим все подкаталоги и файлы в директории
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):  # Проверяем только Python файлы
                module_name = os.path.splitext(file)[0]
                module_path = os.path.join(root, file)

                try:
                    # загружаем модуль с использованием importlib
                    loader = importlib.machinery.SourceFileLoader(module_name, module_path)
                    module = loader.load_module()

                    # Ищем все классы, которые являются подклассами base_class
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if isinstance(obj, type) and issubclass(obj, base_class) and obj is not base_class:
                            check_classes.add(obj)

                except Exception as e:
                    print(f"Error loading module {module_name}: {e}")

    return check_classes


def resolve_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(__file__), path)
