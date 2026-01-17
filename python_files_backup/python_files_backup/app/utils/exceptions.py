# app/utils/exceptions.py

class NotFoundException(Exception):
    """
    Exception personnalisée à lever lorsque'une ressource n'est pas trouvée
    dans la base de données.
    """
    def __init__(self, detail: str):
        self.detail = detail