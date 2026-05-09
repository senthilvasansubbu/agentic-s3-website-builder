# 🚀 Agentic AI Website Builder

An intelligent, conversational AI system that creates beautiful, responsive websites using a multi-agent architecture powered by **CrewAI** and **OpenAI GPT-4**.

## ✨ Features

- **🤖 Multi-Agent System**: UI/UX Designer Agent + Web Developer Agent
- **💬 Conversational Interface**: Describe what you want in natural language
- **🎨 Automatic Design Generation**: AI creates design specifications
- **💻 Complete Code Generation**: Full HTML/CSS/JavaScript output
- **📁 Local Storage**: Save websites to the `output/` folder
- **☁️ S3 Integration**: Optionally upload to AWS S3 (when configured)
- **🎯 Production-Ready**: Clean, semantic, responsive code

## 📋 Prerequisites

- Python 3.8+
- OpenAI API Key (for GPT-4)
- (Optional) AWS credentials for S3 uploads

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/senthilvasansubbu/agentic-ai-website-builder.git
   cd agentic-ai-website-builder   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** — create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4                  # optional, defaults to gpt-4

   # Optional — only needed for S3 uploads
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your_bucket_name
   ```

## 🚀 Usage

```bash
python main.py
```

Describe the website you want in plain English when prompted. Examples:

- `"Create a modern portfolio website for a photographer with a gallery, about page, and contact form"`
- `"Build a landing page for a tech startup with dark theme, pricing table, and feature highlights"`
- `"Design a restaurant website with menu display, reservation form, and location information"`

Generated HTML files are saved to the `output/` folder. If AWS credentials are configured, the file is also uploaded to S3.

Type `exit` or `quit` to stop the application.

## 🗂️ Project Structure

```
agentic-ai-website-builder/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── agents/
│   ├── crew.py              # CrewAI crew orchestration
│   ├── designer_agent.py    # UI/UX Designer agent (design specification)
│   └── developer_agent.py   # Web Developer agent (HTML/CSS/JS generation)
├── config/
│   └── settings.py          # Environment configuration
├── tools/
│   ├── html_generator.py    # Saves generated HTML to disk
│   └── s3_uploader.py       # Optional AWS S3 upload helper
└── output/                  # Generated website files
```

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `crewai` | 1.14.1 | Multi-agent orchestration framework |
| `openai` | 2.32.0 | OpenAI API client (GPT-4) |
| `python-dotenv` | 1.1.1 | Load environment variables from `.env` |
| `boto3` | 1.42.90 | AWS SDK for S3 uploads |
| `requests` | 2.32.5 | HTTP requests |

## 🏗️ How It Works

1. **Designer Agent** — receives your description and produces a detailed design specification (layout, colour scheme, typography, components).
2. **Developer Agent** — takes the design spec and generates a complete, production-ready HTML/CSS/JavaScript file.
3. **HTML Generator** — writes the output file to the `output/` folder with a timestamped filename.
4. **S3 Uploader** — optionally publishes the file to an S3 bucket and returns a public URL.

## 📋 Prerequisites

- Python 3.9+
- OpenAI API Key
- (Optional) AWS credentials for S3 uploads