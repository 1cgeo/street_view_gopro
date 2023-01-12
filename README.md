# **STREET VIEW GOPRO**

### **PROCESSAMENTO**
    
1. Rederizar as imagens Fisheye gerada pela câmera.
    
    > No meu caso eu fiz uso da câmera gopro fusion e usei o Fusion Studio 1.3.

2. a pasta "street_view_plugin" é um plugin do Qgis criado para auxiliar na criação dos metadados para o site. Diante disso, após instalarmos vamos utiliza-lo da seguinte forma:

    > **Note:**
    > Vale destacar que há vários problemas que podem surgi que depende de análise e correção manual.

    1. Selecione o plugin.

        ![](./doc/plugin.png)

    2. Selecione a pasta o as imagens renderizadas e o .csv com os dados do GPS e click em "Gerar pontos".

        ![](./doc/metadado1.png)

        > **Atenção:**
        > Esse arquivo .csv dos dados do GPS foi uma adaptação que foi feita, pois a Gopro Fusion no modo fotografia por lapso de tempo ela não registra o giroscópio na image. Por isso, foi utilizado um GPS durante as fotografias para captura o giroscópio.

    3. O passo anterior vai gerar a malha de pontos das fotografias realizando algumas limpezas de caminhas duplicados, distância e mergeando alguns dados, por exemplo, o giroscópio do GPS.

        ![](./doc/map.png)

        > **Note:**
        > A camada de pontos gerada tem um estilo baseado em cor que informa o conjuto de fotos por faixa.

    4. Criar camada do tipo geométrico linha para realizar as conexões das faixas de imagens

        ![](./doc/connect1.png)

        ![](./doc/connect2.png)

    5. Após o passo anterior haverá as seguintes camadas:
        
        ![](./doc/layers.png)

        > **Atenção:**
        > No final de tudo é importante salvar esse projeto para que futuras modificações sejam rápidas.

    6. Agora deverá ser feito a conexão entre as faixas das imagens. Cada linha deve ter apenas dois pontos de conexão:

        > **Note:**
        > É importante utilizar uma imagem de satélite da área fotografada para confirma se há realmente uma conexão.

        ![](./doc/connect3.png)

    6. Agora deverá ser gerado os metadados que seram utilizados no site. Para isso, basta selecionar os pontos de imagem, as conexões e uma pasta de saída:

### **SITE**


