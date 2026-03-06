<img width="1479" height="971" alt="screenshot" src="https://github.com/user-attachments/assets/8d2ce891-a961-42f6-91cb-7b938c67005f" />

# Discord Drive
Semantically search for vectorized images across your Discord server. (TLDR: Find images with words)

## How it works (two ways)
1. **Manual Tagging:** if the user manually tags an image with the tag `cat`, searching `cat` should append it to the top of the search query.
2. **Semantic fallback:** if there are no strong tag matches, the system uses OPENCLIP to embed and find visually/semantically similar images.

(Search for an image of a cat and find a cat. Search for an image containing the word hello and find that image.)

## Technical
### Repo structure (typical)
- `bot/` – Discord bot (ingestion + admin commands)
- `backend/` – API, embedding calls, Qdrant integration
- `frontend/` – web UI (search + tag editing)
- `docker-compose.yml` – local dev stack

### Run locally 
1. create .env files (auto setup for self-usage soon)   
2. Start everything:
   ```bash
   docker compose up --build
   ```
   Stop everything:
   ```bash
   docker compose down
   ```
---

### Usage
Use this at your own risk. Run this locally, shipping this feature without proper planning and understanding (vibe shipping), could be considered a security breach of you and your server members information as it would be publically accessible.


