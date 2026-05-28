class RPAException(Exception):
    """Exceção base para erros do RPA."""

    pass


class CriticalImageNotFoundError(RPAException):
    """Exceção para imagens críticas não encontradas."""

    def __init__(self, image_name, context=""):
        self.image_name = image_name
        self.context = context
        super().__init__(f"Imagem crítica não encontrada: {image_name}. {context}")


class BusinessError(RPAException):
    """Exceção para erros de negócio que não devem ter retry."""

    def __init__(self, message, status_id):
        self.status_id = status_id
        super().__init__(message)


class CNPJBlockedMessageError(BusinessError):
    """CNPJ está com mensagem pendente (Status 14)."""

    def __init__(self, context=""):
        super().__init__("CNPJ está com mensagem pendente", 14)


class InvalidCNPJError(BusinessError):
    """CNPJ inválido (Status 15)."""

    def __init__(self, context=""):
        super().__init__("CNPJ inválido", 15)
