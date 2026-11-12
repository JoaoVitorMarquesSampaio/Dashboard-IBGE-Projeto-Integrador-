import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import requests
from pathlib import Path

st.set_page_config(page_title='Números que Falam | IBGE + INEP',page_icon='📊',layout='wide')
BASE=Path(__file__).parent/'dados'
st.title('📊 Números que Falam — Descobrindo o Brasil')
st.caption('Projeto Integrador | 2. Curso Superior e 6. Trabalho e Emprego | Fontes oficiais IBGE e INEP')

def ler_upload(upload):
    if upload is None:return None
    try:
        return pd.read_excel(upload) if upload.name.lower().endswith('xlsx') else pd.read_csv(upload,sep=None,engine='python')
    except Exception as e:
        st.error(f'Não foi possível ler o arquivo: {e}')
        return None

def resumo(serie):
    s=pd.to_numeric(serie,errors='coerce').dropna()
    if s.empty:return
    q1,q3=s.quantile([.25,.75]); iqr=q3-q1
    valores={'Média':s.mean(),'Mediana':s.median(),'Moda':s.mode().iloc[0] if not s.mode().empty else np.nan,'Q1':q1,'Q3':q3,'IQR':iqr,'Amplitude':s.max()-s.min(),'Desvio padrão':s.std(ddof=0),'Outliers':int(((s<q1-1.5*iqr)|(s>q3+1.5*iqr)).sum())}
    cols=st.columns(5)
    for i,(k,v) in enumerate(valores.items()):cols[i%5].metric(k,f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.'))
    st.caption('Estatísticas calculadas sobre as observações exibidas, sem ponderação populacional. Outliers: regra 1,5 × IQR.')

@st.cache_data(ttl=86400,show_spinner=False)
def sidra_uf():
    # Tabela 4099: taxa de desocupação, variável 4103; trimestres de 2012 e 2022, 27 UFs.
    # SIDRA usa códigos de trimestre AAAA01..AAAA04.
    url='https://apisidra.ibge.gov.br/values/t/4099/n3/all/v/4103/p/201201,201202,201203,201204,202201,202202,202203,202204?formato=json'
    resp=requests.get(url,timeout=35,headers={'User-Agent':'Projeto-Integrador-Escolar/1.0'})
    resp.raise_for_status(); data=resp.json()
    if not isinstance(data,list) or len(data)<2:raise ValueError('API retornou dados vazios')
    head=data[0]; rows=pd.DataFrame(data[1:])
    # Campos da API SIDRA: D1N=UF, D2N=período, V=valor, D1C=código.
    if not {'D1N','D2C','V'}.issubset(rows.columns):raise ValueError(f'Formato inesperado da API: {list(rows.columns)}')
    rows['taxa']=pd.to_numeric(rows['V'].str.replace(',','.',regex=False),errors='coerce')
    rows['periodo']=rows['D2C'].astype(str)
    rows['ano']=pd.to_numeric(rows['periodo'].str[:4],errors='coerce')
    rows['trimestre']=pd.to_numeric(rows['periodo'].str[-2:],errors='coerce')
    rows['uf']=rows['D1N']
    return rows.loc[rows['ano'].isin([2012,2022]) & rows['trimestre'].between(1,4),['uf','ano','trimestre','taxa']].dropna()

@st.cache_data(ttl=86400,show_spinner=False)
def sidra_brasil():
    url='https://apisidra.ibge.gov.br/values/t/4099/n1/all/v/4103/p/201201,201202,201203,201204,202201,202202,202203,202204?formato=json'
    r=requests.get(url,timeout=35);r.raise_for_status();rows=pd.DataFrame(r.json()[1:]);rows['taxa']=pd.to_numeric(rows['V'],errors='coerce');rows['ano']=rows['D2C'].str[:4].astype(int)
    return rows.groupby('ano',as_index=False)['taxa'].mean()

pagina=st.sidebar.radio('Indicador',['2. Curso Superior','6. Trabalho e Emprego'])
st.sidebar.markdown('**Fontes**: INEP (Censo da Educação Superior 2022) e IBGE (PNAD Contínua / SIDRA, tabela 4099).')
if pagina.startswith('2.'):
    st.header('🎓 2. Curso Superior')
    st.write('**Persona:** governadores interessados em atrair profissionais qualificados e ampliar a presença de mulheres em STEM.')
    st.info('Os dados incluídos são nacionais, não estaduais. Não é correto apresentar percentuais do Brasil como se fossem de MG, SP, ES, RJ ou outros estados. Para comparações por UF, carregue uma base estadual adicional.')
    serie=pd.read_csv(BASE/'concluintes_serie_inep.csv')
    area=pd.read_csv(BASE/'concluintes_inep_2022.csv')
    st.sidebar.subheader('Filtros de curso superior')
    anos=st.sidebar.slider('Intervalo de anos',2012,2022,(2012,2022))
    grupos=st.sidebar.multiselect('Área de conhecimento',sorted(area.grupo.unique()),default=sorted(area.grupo.unique()))
    sexo=st.sidebar.selectbox('Sexo no gráfico',['Ambos','Mulheres','Homens'])
    estado=st.sidebar.selectbox('Abrangência',['Brasil (dados disponíveis)'])
    upload=st.sidebar.file_uploader('Base adicional de Curso Superior (CSV/XLSX)',type=['csv','xlsx'],key='superior')
    if upload is not None:
        extra=ler_upload(upload)
        if extra is not None:
            st.subheader('Base adicional enviada');st.dataframe(extra,use_container_width=True)
            st.caption('Os dados adicionais são exibidos sem serem combinados automaticamente com a série nacional, pois podem ter definições diferentes.')
    fil=serie[serie.ano.between(*anos)]
    st.subheader('Evolução do número de concluintes — Brasil')
    st.plotly_chart(px.line(fil,x='ano',y='concluintes',markers=True,labels={'ano':'Ano','concluintes':'Concluintes'},title='Concluintes de graduação (quantidade, não taxa)'),use_container_width=True)
    resumo(fil.concluintes)
    a=area[area.grupo.isin(grupos)].copy()
    st.subheader('Participação por sexo entre concluintes — Brasil, 2022')
    if not a.empty:
        if sexo=='Mulheres':colunas=['mulheres_pct']
        elif sexo=='Homens':colunas=['homens_pct']
        else:colunas=['mulheres_pct','homens_pct']
        longo=a.melt(id_vars=['area','grupo'],value_vars=colunas,var_name='sexo',value_name='percentual')
        longo['sexo']=longo['sexo'].map({'mulheres_pct':'Mulheres','homens_pct':'Homens'})
        fig=px.bar(longo,y='area',x='percentual',color='sexo',orientation='h',barmode='stack',labels={'area':'Área do curso','percentual':'Percentual (%)'},title='Distribuição percentual por sexo e área geral')
        fig.update_layout(yaxis={'categoryorder':'total ascending'});st.plotly_chart(fig,use_container_width=True)
        st.plotly_chart(px.box(a,x='grupo',y='mulheres_pct',points='all',title='Dispersão da participação feminina entre áreas de cursos'),use_container_width=True)
        resumo(a.mulheres_pct)
    st.warning('Percentuais por sexo são de **concluintes**, não de ingressantes. Não foram incluídos percentuais estaduais nem taxa de conclusão por falta de base estadual verificada.')
    st.markdown('**Leitura para os governadores:** em 2022, mulheres representavam 15,3% dos concluintes em Computação/TIC e 35,1% em Engenharia, contra 78,3% em Educação. Uma política de bolsas, mentoria e permanência feminina em STEM pode ser avaliada com dados estaduais complementares.')
    st.markdown('**Fontes e contexto:** [Apresentação oficial INEP — Censo Superior 2022](https://download.inep.gov.br/educacao_superior/censo_superior/documentos/2022/apresentacao_censo_da_educacao_superior_2022.pdf) · [Sinopses por município/UF](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-superior)')
else:
    st.header('💼 6. Trabalho e Emprego')
    st.write('**Personas:** Márcia (Ministra do Trabalho), Renato (Indústria) e Sílvia (Sebrae). Comparação de desemprego em 2012 e 2022.')
    st.sidebar.subheader('Filtros de trabalho')
    upload=st.sidebar.file_uploader('Base de trabalho adicional (CSV/XLSX)',type=['csv','xlsx'],key='trabalho')
    try:
        df=sidra_uf()
        if df.empty:raise ValueError('Nenhum registro trimestral válido retornado')
        st.success('Taxas trimestrais oficiais obtidas da API SIDRA/IBGE.')
    except Exception as exc:
        df=pd.DataFrame();st.error(f'Não foi possível acessar os dados oficiais da API nesta execução: {exc}. Conecte-se à internet e atualize a página.')
    if upload is not None:
        extra=ler_upload(upload)
        if extra is not None:
            st.subheader('Base adicional enviada');st.dataframe(extra,use_container_width=True)
            st.caption('Não combinada automaticamente com taxas oficiais: indicadores de informalidade, renda e desemprego têm denominadores distintos.')
    if not df.empty:
        estados=sorted(df.uf.unique())
        ufs=st.sidebar.multiselect('UF',estados,default=estados)
        anos=st.sidebar.multiselect('Ano',[2012,2022],default=[2012,2022])
        st.sidebar.selectbox('Sexo',['Total (disponível na consulta oficial)'],help='O recorte por sexo exige outra consulta SIDRA, não incluída nesta extração.')
        st.sidebar.selectbox('Setor',['Todos (sem recorte setorial)'])
        st.sidebar.selectbox('Escolaridade',['Todas (sem recorte de escolaridade)'])
        d=df[df.uf.isin(ufs)&df.ano.isin(anos)]
        # Média aritmética dos quatro trimestres: não é uma taxa anual ponderada.
        anual=d.groupby(['uf','ano'],as_index=False).taxa.mean()
        st.subheader('Taxa média dos trimestres de desocupação por UF')
        st.caption('A média simples das quatro taxas trimestrais é uma aproximação descritiva; não equivale necessariamente à taxa anual oficial ponderada.')
        if not anual.empty:
            fig=px.bar(anual,x='uf',y='taxa',color='ano',barmode='group',labels={'uf':'UF','taxa':'Taxa de desocupação (%)','ano':'Ano'},title='2012 × 2022 — taxas trimestrais médias')
            st.plotly_chart(fig,use_container_width=True)
            resumo(anual.taxa)
            st.plotly_chart(px.box(anual,x='ano',y='taxa',points='all',hover_name='uf',title='Distribuição das taxas entre UFs e possíveis outliers'),use_container_width=True)
            p=anual.pivot(index='uf',columns='ano',values='taxa')
            if {2012,2022}.issubset(p.columns):
                p['variacao_pp']=p[2022]-p[2012]
                p=p.sort_values('variacao_pp')
                st.subheader('Variação de 2012 a 2022 (pontos percentuais)')
                st.plotly_chart(px.bar(p.reset_index(),x='uf',y='variacao_pp',title='Redução (negativo) ou aumento (positivo) da taxa'),use_container_width=True)
                st.metric('Maior queda da taxa',f'{p.index[0]} ({p.iloc[0]["variacao_pp"]:+.2f} p.p.)')
                st.caption('Maior queda na **taxa**, não necessariamente maior redução no número absoluto de desempregados.')
            st.dataframe(anual,use_container_width=True)
            st.download_button('Baixar taxas agregadas CSV',anual.to_csv(index=False).encode('utf-8-sig'),'desocupacao_uf_2012_2022.csv','text/csv')
    st.warning('O painel não atribui números fictícios a informalidade, renda, gênero, setor ou escolaridade. Esses gráficos dependem de bases oficiais adicionais. A comparação por UF funciona quando a API do IBGE está acessível.')
    st.markdown('**Recomendação para a mesa de negociação:** priorizar UFs com desemprego persistente, combinar políticas de qualificação e formalização e avaliar diferenças de remuneração com bases específicas antes de propor metas.')
    st.markdown('**Fontes e contexto:** [API SIDRA — tabela 4099](https://apisidra.ibge.gov.br/values/t/4099/n3/all/v/4103/p/201201,201202,201203,201204,202201,202202,202203,202204) · [PNAD Contínua — IBGE](https://www.ibge.gov.br/estatisticas/sociais/trabalho/17270-pnad-continua.html)')
