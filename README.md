# Dashboard IBGE — Curso Superior e Trabalho e Emprego

Projeto Streamlit com apenas os indicadores 2 e 6 do guia de Projeto Integrador.

## Executar

1. Instale Python 3.10 ou superior.
2. Abra esta pasta no VS Code e execute no terminal:

```bash
pip install -r requirements.txt
streamlit run app.py
```

O indicador de Curso Superior funciona offline com dados nacionais oficiais de 2012–2022 (Inep). O indicador Trabalho e Emprego consulta a API do SIDRA/IBGE pela internet; sem conexão, mostra um aviso e não fabrica resultados.

## Fontes

- INEP: https://download.inep.gov.br/educacao_superior/censo_superior/documentos/2022/apresentacao_censo_da_educacao_superior_2022.pdf
- IBGE: https://apisidra.ibge.gov.br/values/t/4099/n3/all/v/4103/p/201201,201202,201203,201204,202201,202202,202203,202204

## Limitações importantes

- Os dados do INEP embutidos são do Brasil, não das UFs; representam número de concluintes e composição por sexo, não taxa de graduação ou ingressantes por UF.
- A seção de trabalho calcula média simples de taxas trimestrais por UF. Não é uma taxa anual ponderada e não mede número absoluto de pessoas desempregadas.
- Não há simulação de dados oficiais para recortes não obtidos (informalidade, renda, gênero por UF etc.).
