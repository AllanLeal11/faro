# Faro — Scam Shield

Especificación del proyecto para Claude Code. Léela completa antes de trabajar.
Creado: 10 de septiembre de 2026.

## 1. Qué es Faro

Faro es un protector personal contra estafas. No es un simple verificador de mensajes:

- **Analiza mensajes sospechosos** (SMS, correo, WhatsApp pegado como texto) y da un veredicto con evidencia verificable, nivel de confianza y una explicación simple.
- **Conoce el contexto del usuario:** guarda su "círculo de confianza" (su banco real, dominios y números oficiales, contactos de confianza) y detecta cuando alguien se hace pasar por *esas* entidades.
- **Activa la red familiar:** si el riesgo es alto, avisa a un familiar de confianza con una pregunta de verificación sugerida.
- **Mide su precisión** con datasets públicos y la publica.

Público: general. Caso de demo principal: una persona mayor recibe un SMS falso de su banco.

## 2. Reglas de trabajo (obligatorias)

1. **Idioma:** habla con Allan en español. Todo el código, comentarios, commits, README, textos de la interfaz y documentación de entrega van en **inglés** (las reglas de ambos hackathons exigen materiales en inglés). La interfaz debe tener opción de español.
2. **Allan decide el producto.** Las reglas exigen que la idea y la creatividad sean suyas. Antes de cambiar el alcance, agregar funciones o tomar decisiones de producto, pregúntale.
3. **Secretos:** nunca escribas API keys en el código ni en commits. Usa variables de entorno, mantén `.env.example` actualizado y `.env` en `.gitignore`.
4. **Seguridad:** Faro **nunca abre, visita ni descarga** los enlaces de los mensajes analizados. Solo analiza el texto de las URLs y busca información *sobre* el dominio.
5. **Privacidad:** los mensajes analizados **no se guardan** en la base de datos. Solo se guarda el círculo de confianza, los contactos familiares y metadatos de alertas (sin el contenido del mensaje).
6. **Modo mock:** con `MOCK_MODE=true` todo debe funcionar sin claves (respuestas simuladas del LLM y de Tavily). Así se puede desarrollar antes de tener las claves.
7. **Commits pequeños y frecuentes**, con mensajes claros en inglés.
8. **Friction log:** cada vez que una herramienta de Amazon (MCP, AWS) cause un problema, anótalo en `docs/friction-log.md` con: tarea, pasos, resultado esperado vs. real, severidad, solución temporal y sugerencia. Allan revisa y confirma cada entrada.
9. **No inventes datos técnicos.** Si no estás seguro de un ID de modelo, endpoint o versión de SDK, consulta la documentación oficial antes de usarlo.
10. **Seguridad desde el inicio:** la sección 12 es obligatoria en cada función que construyas, no una tarea para el final. Si una regla de seguridad choca con una función, avisa a Allan antes de relajarla.

## 3. Alcance

### Obligatorio (MVP)
1. **Análisis de mensajes** con veredicto, evidencia, confianza y explicación.
2. **Círculo de confianza:** CRUD de entidades de confianza (banco, empresa, contacto) con dominios, teléfonos y correos oficiales.
3. **Alerta familiar:** correo a un contacto familiar con la pregunta de verificación sugerida.
4. **Servidor MCP** con herramientas `check_message`, `add_trusted_contact` y `alert_family`.
5. **Simulación de Alexa+ en la web:** entrada por voz y respuesta hablada que usa las mismas herramientas.
6. **Script de evaluación** con métricas publicadas en el README.

### Fuera de alcance (solo si sobra tiempo y Allan lo aprueba)
- Análisis de capturas de pantalla (OCR).
- Integración directa con WhatsApp (posible con n8n).
- App móvil nativa.

## 4. Arquitectura

```
[React web] ──HTTP──▶ [FastAPI backend] ◀──MCP (Streamable HTTP)── [Clientes MCP / Alexa+]
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
  Nebius Token Factory   Tavily API       PostgreSQL
  (Nemotron models)      (evidencia)      (círculo de confianza)
                            │
                        Amazon SES (alertas por correo)
```

### Pipeline de análisis (`backend/app/pipeline/`)

1. **extract.py — Nemotron Nano (rápido):** extrae en JSON: URLs, dominios, teléfonos, correos, organización que dice ser el remitente, acción solicitada (pagar, hacer clic, compartir código, instalar app) y señales de presión (urgencia, amenazas, premios).
2. **checks.py — verificaciones deterministas en Python (sin LLM):**
   - Dominio parecido a uno del círculo de confianza (distancia de edición, caracteres confundibles, punycode).
   - Acortadores de URL, URLs con IP en lugar de dominio.
   - Remitente que no coincide con los datos oficiales guardados.
   - Solicitud de códigos OTP, tarjetas de regalo, criptomonedas o transferencias urgentes.
   - Cada verificación produce un ítem de evidencia con `id`, `type`, `result` y `detail`.
3. **evidence.py — Tavily:** busca el dominio oficial de la organización mencionada y reportes de estafa asociados al dominio o número. Cada resultado es un ítem de evidencia con `id` y `source_url`.
4. **verdict.py — Nemotron Super (razonamiento):** devuelve JSON con `risk_level` (low/medium/high), `confidence` (0–1), `reasons` (cada una con los `evidence_ids` que la respaldan), `explanation` en el idioma del usuario, `recommended_action` y `verification_question`.
5. **pipeline.py — orquestación y validación:**
   - **Regla clave:** el backend descarta cualquier razón que no cite evidencia real producida en los pasos 2 o 3. El modelo no puede inventar evidencia.
   - **Robustez:** si Tavily o el LLM fallan, devolver el resultado solo con las verificaciones deterministas, marcado como `partial: true`.

### Modelos
- Usar modelos open source de NVIDIA (familia Nemotron) servidos en **Nebius Token Factory**. Es requisito del hackathon de Nebius.
- Los IDs exactos de modelo y el `base_url` van en variables de entorno. Verificar en la documentación de Token Factory y en el repositorio `nebius/token-factory-cookbook`. Si la API es compatible con OpenAI, usar el SDK de `openai` con `base_url` configurable.

### Base de datos (PostgreSQL)
- `users`: id, email, password_hash, language, created_at.
- `trusted_entities`: id, user_id, kind (bank/company/contact), name, domains[], phones[], emails[].
- `family_contacts`: id, user_id, name, email, relationship.
- `alerts`: id, user_id, family_contact_id, risk_level, created_at, sent_ok. **Sin contenido del mensaje.**

### API (FastAPI)
- `POST /api/check` — analiza un mensaje.
- `GET/POST/PUT/DELETE /api/trusted` — círculo de confianza.
- `GET/POST/DELETE /api/family` — contactos familiares.
- `POST /api/alert` — envía la alerta familiar.
- `POST /api/auth/register`, `POST /api/auth/login` — JWT simple.
- `GET /health`.
- Cuenta demo precargada (seed) para que los jueces prueben sin registrarse. Las credenciales van en las instrucciones de prueba de la entrega.

### Servidor MCP (`mcp_server/`)
- SDK oficial de MCP para Python, transporte **Streamable HTTP**, especificación **2025-11-25 o posterior** (requisito de Amazon). Verificar que la versión del SDK la soporta.
- Herramientas: `check_message`, `add_trusted_contact`, `alert_family`.
- Reutiliza los mismos servicios del backend. No duplicar lógica.

### Alertas
- Enviar correos con **Amazon SES** (sirve para el mini reto AWS Builder de Amazon). Documentar la integración en el README.
- En modo sandbox de SES solo se puede enviar a correos verificados; es suficiente para la demo.

## 5. Frontend (React + TypeScript, Vite)

Pantallas:
1. **Check a message:** área de texto grande y resultado con nivel de riesgo, explicación, lista de evidencia con fuentes y botón para alertar a un familiar.
2. **Trusted circle:** gestionar entidades de confianza.
3. **Family:** gestionar contactos familiares.
4. **Voice (Alexa+ simulation):** entrada por voz (Web Speech API) y respuesta hablada.
5. **How it works:** explicación del pipeline y resultados de la evaluación.

Dirección de diseño:
- Pensado para personas mayores: texto grande, alto contraste, botones claros, accesible con teclado y lector de pantalla, responsive desde móvil.
- Identidad basada en el concepto de faro (luz que guía, señal en la oscuridad), sin caer en plantillas genéricas de SaaS (tarjetas idénticas con sombra gris, degradados decorativos, etiquetas en mayúsculas sobre cada título).
- Textos en lenguaje simple desde la perspectiva del usuario. Los errores explican qué pasó y qué hacer.
- **Antes de construir la interfaz, propón a Allan una paleta (4–6 colores), tipografías y un wireframe, y espera su aprobación.**

## 6. Evaluación (`eval/`)

- `run_eval.py` compara dos sistemas sobre el mismo conjunto:
  - **Baseline:** una sola llamada a Nemotron sin verificaciones ni evidencia.
  - **Faro:** el pipeline completo.
- Métricas: precision, recall, F1 y tasa de falsos positivos.
- Datasets: públicos, de phishing y estafas por SMS o correo. Documentar fuente y licencia en `eval/datasets/README.md`. No subir datasets cuya licencia no lo permita.
- Muestra balanceada y moderada (por ejemplo 200–400 mensajes) para cuidar los créditos. Cachear resultados.
- Guardar resultados en `eval/results/` y generar una tabla para el README.

## 7. Estructura del repositorio

```
faro/
├── CLAUDE.md
├── README.md
├── LICENSE                  # MIT
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── db/
│   │   ├── pipeline/        # extract, checks, evidence, verdict, pipeline
│   │   └── services/        # alerts (SES), auth
│   └── tests/
├── mcp_server/
├── frontend/
├── eval/
│   ├── run_eval.py
│   ├── datasets/
│   └── results/
└── docs/
    ├── architecture.md
    ├── security.md
    ├── friction-log.md
    ├── feedback-nebius.md
    └── feedback-amazon.md
```

## 8. Variables de entorno

```
MOCK_MODE=true
NEBIUS_API_KEY=
NEBIUS_BASE_URL=
MODEL_EXTRACT=
MODEL_VERDICT=
TAVILY_API_KEY=
DATABASE_URL=
JWT_SECRET=
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
SES_FROM_EMAIL=
FRONTEND_URL=
ENVIRONMENT=development
ALLOWED_ORIGINS=
```

Solo el backend (Railway) tiene claves. El frontend (Vercel) nunca lleva secretos: toda variable `VITE_*` es pública en el navegador.

## 9. Despliegue

- **Railway:** backend FastAPI, servidor MCP y PostgreSQL.
- **Vercel:** frontend.
- La demo pública debe estar disponible gratis para los jueces hasta el fin de la evaluación (15 de diciembre de 2026).

## 10. Calendario

| Fechas | Objetivo |
|---|---|
| Sep 10–16 | Repositorio, estructura, modo mock, `checks.py` con tests, elegir datasets |
| Sep 17–30 | Pipeline completo con Token Factory y Tavily, base de datos, API, servidor MCP |
| Oct 1–9 | Frontend, simulación de voz, alertas con SES, evaluación |
| Oct 10–18 | Despliegue, README, documentación, pulido |
| Oct 19–21 | Video y entrega en Amazon (cierra Oct 23, 12:00 pm PT) |
| Hasta Oct 28 | Ajustes y entrega en Nebius (cierra Oct 30, 10:00 am PT) |

## 11. Checklist de entrega

### Nebius x NVIDIA Global AI Hackathon — track Best Apps and Agents
- [ ] La app hace llamadas en tiempo de ejecución a Token Factory con un modelo open source de NVIDIA.
- [ ] Llamada funcional a Tavily en tiempo de ejecución (bonus Best Use of Tavily).
- [ ] URL de demo pública funcionando.
- [ ] Repositorio público con licencia MIT visible en "About".
- [ ] README con instrucciones de instalación y sección destacando Nemotron, Token Factory y Tavily.
- [ ] Video público en YouTube de menos de 3 minutos, en inglés, con audio, sin música con copyright.
- [ ] Descripción del proyecto en inglés.
- [ ] Feedback sobre Token Factory y herramientas de NVIDIA (`docs/feedback-nebius.md`).

### Build, Ship, Shape: Amazon Developer Hackathon — track Alexa+
- [ ] Servidor MCP (spec 2025-11-25+, Streamable HTTP) llamado de verdad en el código, o la simulación de Alexa+ con su código fuente.
- [ ] Repositorio público en GitHub con licencia visible e instrucciones.
- [ ] Video público en YouTube o Vimeo de menos de 3 minutos, en inglés, mostrando el proyecto funcionando.
- [ ] Feedback de cada herramienta, API o SDK usado (`docs/feedback-amazon.md`).
- [ ] Friction log completo (bonus de hasta 10%).
- [ ] Mini reto AWS Builder: integración con Amazon SES documentada.
- [ ] Mini reto Open Source: URL del repositorio, usuario de GitHub y descripción.

## 12. Seguridad (obligatorio)

Principios: defensa en profundidad, seguro por defecto y **fallar cerrado** (ante la duda, bloquear o marcar riesgo alto). Referencias: OWASP Top 10, OWASP API Security Top 10, OWASP Top 10 for LLM Applications y la especificación de seguridad de MCP. Ningún sistema es invulnerable: el objetivo es cerrar los ataques conocidos y documentar los riesgos restantes.

### 12.1 Secretos y permisos
- Claves solo en variables de entorno del backend en Railway. Nunca en el frontend, en logs ni en prompts.
- Hook de pre-commit con `gitleaks` y activar secret scanning y push protection en GitHub.
- Si una clave se filtra: rotarla de inmediato. Borrar el commit no basta.
- Usuario IAM de AWS con permiso **únicamente** para `ses:SendEmail` desde la identidad verificada.
- Alertas de gasto en Nebius, Tavily y AWS Budgets.

### 12.2 Transporte e intercepción (MITM)
- Solo HTTPS. Redirigir HTTP a HTTPS y enviar `Strict-Transport-Security`.
- Llamadas salientes siempre con verificación TLS (prohibido `verify=False`), con timeouts y solo hacia hosts permitidos: Nebius, Tavily y AWS.
- Cabeceras de seguridad en backend y frontend:
  - `Content-Security-Policy` estricta, sin scripts inline.
  - `X-Content-Type-Options: nosniff`.
  - `frame-ancestors 'none'` contra clickjacking.
  - `Referrer-Policy: strict-origin-when-cross-origin`.
  - `Permissions-Policy` que permita el micrófono solo en el propio origen.
- CORS con lista explícita (`ALLOWED_ORIGINS`). Prohibido `*` con credenciales.
- Tomar la IP del cliente solo de la cabecera del proxy de confianza de Railway, para que no se pueda falsificar `X-Forwarded-For` y evadir límites.
- Conexión a PostgreSQL con SSL y por la red privada de Railway, sin exponer la base de datos a internet.

### 12.3 Autenticación y sesiones
- Contraseñas con Argon2id.
- JWT de corta duración con secreto fuerte. Algoritmo fijo (rechazar `none` y confusión de algoritmos) y validar `exp`, `iss` y `aud`.
- Token en cookie `httpOnly`, `Secure`, `SameSite=Strict`, más token CSRF en toda petición que modifique datos. Nunca guardar tokens en `localStorage`.
- Límite de intentos de login con espera progresiva. Mensajes de error genéricos para no revelar qué correos existen.
- Cuenta demo: sus datos se restauran periódicamente y solo puede enviar alertas a un correo verificado preconfigurado.

### 12.4 Autorización (IDOR / BOLA)
- Toda consulta se filtra por el `user_id` del token. Nunca aceptar `user_id` desde el cuerpo de la petición.
- Acceder a un recurso ajeno devuelve 404, no 403.
- Esquemas Pydantic explícitos con `extra="forbid"` para evitar asignación masiva.
- Tests automáticos que prueben que el usuario A no puede leer, editar ni borrar datos del usuario B.

### 12.5 Validación de entrada e inyecciones clásicas
- **SQL injection:** solo ORM o consultas parametrizadas. Prohibido concatenar texto en SQL.
- **XSS:**
  - Nunca usar `dangerouslySetInnerHTML`.
  - El mensaje analizado y la salida del modelo se muestran como texto plano.
  - Las URLs sospechosas se muestran "desactivadas" y nunca como enlaces clicables, por ejemplo `hxxps://banco-falso[.]com`.
  - Solo las fuentes oficiales de evidencia pueden ser enlaces: únicamente `https` y con `rel="noopener noreferrer nofollow"`.
- **Command injection:** nunca pasar datos del usuario a comandos de shell. Prohibidos `eval`, `exec`, `pickle` y `yaml.load` inseguro.
- **Límites:** mensaje de máximo 5.000 caracteres, límite de tamaño del cuerpo de la petición y validación de formato de correos, teléfonos y dominios.
- **ReDoS:** expresiones regulares acotadas y sin retroceso catastrófico, sumadas a los límites de longitud.
- **Inyección en correos:** eliminar saltos de línea (CR/LF) en asuntos y destinatarios y escapar el contenido de las plantillas.
- **Trucos Unicode:** normalizar con NFKC para el análisis, detectar homoglifos y punycode, y eliminar o hacer visibles los caracteres de control bidireccional (por ejemplo U+202E) al mostrar texto.

### 12.6 SSRF
- Faro nunca hace peticiones a URLs que vengan de los mensajes. Tavily recibe consultas de búsqueda, no URLs para visitar.
- Si en el futuro se agrega cualquier descarga, primero bloquear IPs privadas, `localhost`, `169.254.169.254` y redirecciones, y consultar a Allan.

### 12.7 Seguridad del LLM (OWASP LLM Top 10)
- **Inyección de prompts directa:** el mensaje del usuario siempre va delimitado como *datos no confiables*, con instrucciones de sistema que prohíben seguir órdenes contenidas en él.
- **Inyección indirecta:** los resultados de Tavily también son datos no confiables y reciben el mismo tratamiento.
- **Piso determinista:** si `checks.py` detecta una señal grave (dominio imitador, pedido de OTP, pago con tarjetas de regalo o cripto), el modelo **no puede bajar** el riesgo por debajo de alto.
- **Salida estructurada:** validar el JSON contra un esquema y rechazar lo inválido. Nunca ejecutar ni interpretar como código lo que devuelve el modelo.
- **Sin agencia excesiva:** el modelo no tiene herramientas en el paso de veredicto. Nunca puede enviar alertas ni modificar datos; eso solo ocurre por acción explícita del usuario.
- **Datos sensibles:**
  - Antes de enviar el mensaje al LLM o a Tavily, ocultar números de tarjeta, códigos OTP y contraseñas.
  - A Tavily solo se envían dominios, nombres de organizaciones y números del remitente, nunca datos personales del usuario.
  - Los prompts no contienen secretos.
- **Límites de consumo:** `max_tokens` y timeouts en cada llamada.
- **Pruebas adversarias:** la evaluación incluye mensajes con intentos de inyección y reporta la tasa de resistencia.

### 12.8 Servidor MCP
- Autenticación obligatoria en cada petición con token por usuario. No reenviar tokens del cliente a servicios externos.
- Validar la cabecera `Origin` en Streamable HTTP, como exige la especificación, para prevenir DNS rebinding. En desarrollo local, escuchar solo en `127.0.0.1`.
- IDs de sesión aleatorios criptográficamente, ligados al usuario y nunca usados como autenticación.
- Las entradas de las herramientas usan los mismos esquemas de validación que la API.
- `alert_family` solo acepta contactos del propio usuario y respeta los límites de envío.
- Descripciones de herramientas fijas en el código, nunca generadas con contenido externo (evita "tool poisoning").
- Las respuestas marcan el contenido del mensaje como no confiable y devuelven URLs desactivadas, para no inyectar al cliente que las reciba.

### 12.9 Abuso, disponibilidad y costos (DoS)
- Límite de peticiones por IP y por usuario, en la API y en el servidor MCP. Valores iniciales:
  - `/api/check`: 10 por minuto y 100 por día por usuario.
  - Login: 5 por minuto por IP.
  - Alertas: 3 por día por usuario.
- Timeouts en todas las llamadas externas. Si un proveedor falla, devolver el resultado parcial (`partial: true`) en lugar de colgar el servidor.
- Caché de veredictos por hash del mensaje, con expiración corta y sin guardar el contenido.

### 12.10 Errores, logs y configuración
- En producción: sin trazas de error hacia el cliente, `DEBUG` desactivado y `/docs` de FastAPI deshabilitado o protegido.
- Los logs nunca incluyen contenido de mensajes, contraseñas, tokens ni claves.
- Registrar eventos de seguridad: logins fallidos, límites alcanzados y fallos de autorización.
- `/health` no revela versiones ni información interna.

### 12.11 Dependencias y cadena de suministro
- Versiones fijadas con archivos lock en Python y Node.
- `pip-audit` y `npm audit` en CI, más Dependabot activado.
- Verificar el nombre exacto de cada paquete antes de instalarlo, para evitar typosquatting.
- Contenedores con imagen base mínima y usuario no root.

### 12.12 Pruebas de seguridad antes de entregar
- Análisis estático con `bandit` y `semgrep`, y escaneo de secretos con `gitleaks`.
- Tests automáticos de autorización, payloads de inyección, límites de peticiones y cabeceras de seguridad.
- Escaneo dinámico con OWASP ZAP (baseline) **solo contra el despliegue propio de Faro**. Nunca escanear servicios de terceros (Nebius, Tavily, Railway, Vercel, AWS).
- Documentar el modelo de amenazas, las pruebas y los riesgos restantes en `docs/security.md`, con un resumen en la sección "Security" del README.

## 13. Primer paso sugerido

1. Crear la estructura del repositorio, `.gitignore`, `.env.example` y `LICENSE` MIT.
2. Configurar `gitleaks` como hook de pre-commit.
3. Configurar FastAPI con `MOCK_MODE`, cabeceras de seguridad, CORS restringido y límites de tamaño.
4. Implementar `checks.py` con tests unitarios (no necesita claves).
5. Mostrar a Allan el resultado y confirmar el siguiente paso.
