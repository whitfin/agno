# GitHub Repository Analyzer

An AI-powered GitHub repository analysis tool built with Agno and Streamlit.

## Overview

GitHub Repository Analyzer provides comprehensive insights into GitHub repositories, including code quality assessment, contribution patterns, issue and PR analysis, and community health evaluation. The application presents the analysis in an interactive Streamlit dashboard with visualizations.

## Features

- **Repository Analysis**: Stars, forks, watchers, contributor statistics, commit activity
- **Issue Analysis**: Issue categorization, response time, trending topics
- **Pull Request Analysis**: PR lifecycle analysis, code review metrics
- **Statistical Visualizations**: Interactive charts for repository metrics
- **Repository Comparison**: Compare metrics across multiple repositories
- **Favorites Management**: Save frequently analyzed repositories
- **Export Options**: Download reports in markdown format

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your GitHub access token:
   ```
   GITHUB_ACCESS_TOKEN=your_token_here
   ```

## Usage

Run the Streamlit app:

```
streamlit run app.py
```

This will open a web interface where you can:

- Enter a repository name in the format `owner/repo`
- Configure analysis options
- View interactive visualizations
- Compare multiple repositories
- Save favorite repositories for quick access

## Project Structure

The project uses a streamlined structure with all functionality in a single file:

```
github-repo-analyzer/
├── main.py           # Main application with all functionality
├── requirements.txt  # Dependencies
├── README.md         # Documentation
├── .env              # Environment variables (gitignored)
└── output/           # Generated analysis reports
```

## Technologies Used

- [Agno](https://docs.agno.com) - AI agent framework for GitHub analysis
- [Streamlit](https://streamlit.io/) - Interactive web interface
- [Matplotlib](https://matplotlib.org/) - Data visualization
- [PyGithub](https://pygithub.readthedocs.io/) - GitHub API access
