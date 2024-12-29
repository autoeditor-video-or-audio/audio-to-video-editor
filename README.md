# Audio-to-Video Editor

Audio-to-Video Editor é uma ferramenta automatizada desenvolvida para facilitar a criação de vídeos verticais com áudio transcrito e legendas geradas dinamicamente. Este projeto utiliza tecnologias modernas para integrar armazenamento, transcrição e edição de vídeo em um fluxo de trabalho eficiente.

## Funcionalidades

- **Transcrição de Áudio:** Converte arquivos de áudio em texto utilizando APIs externas de transcrição.
- **Geração de Legendas:** Cria legendas sincronizadas com base no texto transcrito, utilizando MoviePy para inseri-las no vídeo.
- **Edição de Vídeo:** Gera vídeos verticais cortados e sincronizados com o áudio fornecido.
- **Integração com MinIO:** Armazena e recupera arquivos diretamente de buckets configurados.
- **Automação Completa:** Um pipeline automatizado que realiza todas as etapas, desde o upload do áudio até a criação do vídeo final.

## Pré-requisitos

Certifique-se de que sua máquina atenda aos seguintes requisitos:

- Python 3.8 ou superior
- Dependências do projeto listadas em `requirements.txt`
- Servidor MinIO configurado
- API de transcrição disponível e acessível

## Instalação

1. Clone o repositório:

   ```bash
   git clone https://github.com/seu-usuario/audio-to-video-editor.git
   cd audio-to-video-editor
   ```

2. Crie e ative um ambiente virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

## Configuração

Configure as variáveis de ambiente necessárias para o funcionamento do projeto:

- `MINIO_URL`: URL do servidor MinIO
- `MINIO_PORT`: Porta do servidor MinIO
- `MINIO_ROOT_USER`: Usuário root do MinIO
- `MINIO_ROOT_PASSWORD`: Senha root do MinIO
- `API_TRANSCRIBE_URL`: URL da API de transcrição
- `API_TRANSCRIBE_PORT`: Porta da API de transcrição
- `API_TRANSCRIBE_TIMEOUT`: Tempo limite para as requisições à API de transcrição

Você pode configurar essas variáveis em um arquivo `.env` e carregá-las utilizando a biblioteca `python-dotenv`.

## Uso

1. Execute o script principal:

   ```bash
   python main.py
   ```

2. O pipeline automatizado será iniciado, realizando as seguintes etapas:

   - Verificação de arquivos no bucket MinIO
   - Download de arquivos de áudio e background
   - Transcrição de áudio
   - Criação de vídeo com base no áudio e legendas
   - Upload do vídeo final para o bucket

3. Logs serão exibidos no console para acompanhar o progresso.

## Estrutura do Projeto

```
.
├── main.py                # Script principal
├── utils.py               # Funções utilitárias
├── requirements.txt       # Dependências do projeto
├── README.md              # Documentação do repositório
├── foredit/               # Diretório temporário para edição
├── edited/                # Diretório temporário para vídeos finalizados
└── .env                   # Arquivo de configuração de variáveis de ambiente (opcional)
```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests com sugestões de melhorias ou novas funcionalidades.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
