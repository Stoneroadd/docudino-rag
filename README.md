# DocuDino 🦕

**Pregúntale a tus documentos. DocuDino trae las pruebas.**

RAG de escritorio por CLI: indexa PDF/DOCX/TXT/Markdown, recupera fragmentos localmente con BM25 y consulta el LLM que elijas. Cada respuesta debe citar fuentes tipo `[S1]`; el CLI comprueba que esas referencias existan entre los fragmentos enviados.

## Inicio rápido

Requiere Python 3.10+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
docudino init
docudino docs add examples/guide-sample.md
```

Con [Ollama](https://ollama.com/) instalado y un modelo descargado:

```powershell
$env:DOCUDINO_OLLAMA_MODEL = "gemma4"
docudino ask "¿Qué revisa el control de calidad?" --provider ollama
```

Para PDF/DOCX importa el archivo del usuario:

```powershell
docudino docs add "C:\documentos\manual.pdf" "C:\documentos\procedimiento.docx"
docudino docs list
docudino ask "¿Cuándo se publica el reporte?" --provider ollama --model gemma4 --top-k 4
```

## Conectar proveedores

- `ollama`: ejecución local por defecto; define `DOCUDINO_OLLAMA_MODEL`. El endpoint nativo de chat usa `POST /api/chat` con `stream: false`, según [la documentación de Ollama](https://docs.ollama.com/api/chat).
- `openai`: `OPENAI_API_KEY` y `DOCUDINO_OPENAI_MODEL`; usa Responses API.
- `anthropic`: `ANTHROPIC_API_KEY` y `DOCUDINO_ANTHROPIC_MODEL`; usa Messages API.
- `openai-compatible`: define `DOCUDINO_LLM_BASE_URL`, `DOCUDINO_LLM_MODEL` y opcionalmente `DOCUDINO_LLM_API_KEY` para gateways que acepten Chat Completions.

Ejemplo remoto:

```powershell
$env:OPENAI_API_KEY = "..."
$env:DOCUDINO_OPENAI_MODEL = "..."
docudino ask "Resume el procedimiento de respaldo" --provider openai --allow-external
```

El flag `--allow-external` es obligatorio para endpoints remotos. DocuDino envía solamente la pregunta y los fragmentos recuperados, no el índice completo. Revisa las políticas de retención y privacidad de tu proveedor antes de usar documentos sensibles. No guardes claves ni tus documentos en Git.

## Búsqueda y citas

BM25 ordena fragmentos por coincidencia léxica: términos de la pregunta frente al contenido extraído. DocuDino no usa embeddings ni hace búsquedas web. Reformula la consulta si los documentos usan vocabulario distinto. PDF cita página; DOCX/TXT/Markdown cita párrafo o sección. Las referencias `[S#]` son locales a cada consulta.

La comprobación de citas solo valida que un alias citado fue incluido en el contexto; no demuestra que la respuesta sea correcta. Verifica la afirmación en el archivo original. Los documentos pueden contener instrucciones maliciosas: el prompt los trata como datos, pero no existe una defensa perfecta contra prompt injection. No conectes herramientas de escritura ni automatizaciones con documentos no confiables.

## Privacidad y datos

- `docudino init` crea por defecto `~/.docudino/` (Windows: dentro de tu perfil de usuario), fuera del checkout público.
- El índice conserva texto extraído y metadatos en `corpus.json` local para permitir la búsqueda offline; los archivos originales no se copian.
- Los datos se escriben con permisos restrictivos en sistemas que los admiten. En Windows se aplican las ACL heredadas de tu perfil.
- Eliminar un documento del índice: `docudino docs remove ID`. Esto borra sus fragmentos del índice, no el original.
- Puedes elegir otra carpeta privada con `--home RUTA` o `DOCUDINO_HOME`.

## Límite del MVP

Extracción básica de texto, búsqueda léxica BM25 y generación basada en contexto. No hace OCR de PDFs escaneados, búsqueda semántica vectorial, reranking, control de acceso multiusuario ni evaluación formal de fidelidad. Si un PDF no contiene texto seleccionable, aplícale OCR local antes de importarlo.

## Licencia

MIT. Consulta [`LICENSE`](LICENSE).
