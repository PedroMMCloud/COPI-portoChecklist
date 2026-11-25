# app/erros.py
#
# Erro padrão da API. Em qualquer ponto do código (rotas, serviços), basta fazer:
#
#     raise ErroNegocio(404, "CHECKLIST_NAO_ENCONTRADO", "Checklist não encontrado.")
#
# e o handler abaixo transforma isso numa resposta JSON sempre no mesmo formato:
#
#     {
#       "erro": {
#         "codigo": "CHECKLIST_NAO_ENCONTRADO",
#         "mensagem": "Checklist não encontrado.",
#         "campos": []
#       }
#     }
#
# "campos" é uma lista opcional que indica quais campos têm problema, por exemplo:
#     [{"campo": "horimetro_inicial", "mensagem": "Campo obrigatório."}]

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErroNegocio(Exception):
    """Erro de regra de negócio, com status HTTP, código estável e mensagem legível."""

    def __init__(self, status: int, codigo: str, mensagem: str, campos=None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.campos = campos or []


def _resposta(status: int, codigo: str, mensagem: str, campos: list) -> JSONResponse:
    """Monta a resposta no formato padrão do contrato."""
    return JSONResponse(
        status_code=status,
        content={"erro": {"codigo": codigo, "mensagem": mensagem, "campos": campos}},
    )


async def tratar_erro_negocio(request: Request, exc: ErroNegocio) -> JSONResponse:
    """Handler para os ErroNegocio lançados no código."""
    return _resposta(exc.status, exc.codigo, exc.mensagem, exc.campos)


async def tratar_erro_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler para dados inválidos enviados ao FastAPI (ex.: campo faltando ou com tipo errado).

    Sem isto, o FastAPI devolveria o erro 422 num formato diferente do resto da API.
    """
    campos = [
        {
            # loc é algo como ("body", "horimetro_inicial"); tiramos o "body"/"query" do início
            "campo": ".".join(str(parte) for parte in erro["loc"][1:]),
            "mensagem": erro["msg"],
        }
        for erro in exc.errors()
    ]
    return _resposta(422, "VALIDACAO", "Dados inválidos.", campos)