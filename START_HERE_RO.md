# NEXUS Study AI — Ghid rapid pentru Windows

Interfața aplicației este **100% în engleză**. Acest ghid este în română pentru instalare.

## Ce face aplicația

- Citește PDF-uri care conțin text selectabil, documente DOCX, TXT și MD.
- Răspunde la întrebări despre materiale, folosind fragmente și indicatoare de sursă.
- Generează rezumate, quiz-uri cu variante de răspuns și flashcard-uri.
- Rulează AI local prin **Ollama**, fără abonament API.

## Instalare — pas cu pas

1. Descarcă arhiva `.zip` din ChatGPT.
2. În **Downloads**, click dreapta pe arhivă → **Extract All** → **Extract**.
3. Intră în folderul extras `NEXUS_Study_AI_v0.1.0`.
4. Verifică dacă ai **Python 3.12** instalat. În File Explorer, în bara de adresă scrie `cmd`, apoi Enter. Tastează:

   `py -3.12 --version`

5. Verifică Ollama și modelele instalate:

   `ollama list`

   Dacă apare `qwen2.5:3b`, e perfect. Dacă lipsește, îl poți descărca prin:

   `ollama pull qwen2.5:3b`

   Pentru prima instalare a modelului ai nevoie de internet. De obicei, Ollama pornește automat pe Windows.

6. Revino în File Explorer și dă dublu-click pe **`run.bat`**. Prima pornire instalează automat două biblioteci Python în folderul `.venv`.
7. În NEXUS Study AI, apasă **Refresh Installed Models**. Alege `qwen2.5:3b`.
8. Apasă **Add Documents** și selectează un PDF, DOCX, TXT sau MD. Apoi încearcă:

   - **Ask AI**: întreabă ceva despre document.
   - **Summary**: apasă **Generate Summary**.
   - **Quiz**: apasă **Generate 5 Questions** și răspunde la întrebări.
   - **Flashcards**: apasă **Generate Flashcards**, apoi **Reveal / Hide**.

## Vrei să testezi cu materiale deja pregătite?

Din Command Prompt, aflat în folderul proiectului, rulează:

`py -3.12 make_demo.py`

Apare folderul `_DEMO_NOTES` cu trei fișiere demonstrative. Încarcă `physics_notes.txt` și întreabă „What is acceleration?”.

## Cum fac fișierul .exe?

După testarea aplicației, dă dublu-click pe **`build.bat`**. Fișierul rezultat se va găsi în `dist\NEXUS_Study_AI.exe`.

**Atenție:** executabilul nu include Ollama și nici modelul de AI. Pe fiecare calculator care folosește NEXUS Study AI trebuie instalate separat Ollama și un model local.

## Probleme frecvente

- **Cannot reach Ollama**: deschide Ollama. Verifică în CMD cu `ollama list`. Dacă Ollama nu rulează, pornește aplicația sau serviciul Ollama.
- **Python 3.12 not found**: verifică `py -3.12 --version`; instalează Python 3.12 dacă lipsește.
- **No selectable text found**: PDF-ul este probabil scanat. Versiunea actuală nu face OCR.
- **The AI produced too few valid questions**: modelul a returnat un JSON incorect. Încearcă încă o dată sau selectează un model mai bun.
- **Merge greu**: modelele locale pot avea nevoie de timp. Pentru un PC modest, încearcă `qwen2.5:3b` și un document de 1–3 pagini pentru primul test.
- **Eroare în CMD**: lasă fereastra deschisă și fă un screenshot cu mesajul, apoi trimite-l în ChatGPT.

## Confidențialitate și limite

Conținutul documentelor se transmite **doar** către Ollama pe propriul calculator (`127.0.0.1`). Nu este urcat pe un server AI extern de către această aplicație. Instalarea bibliotecilor și descărcarea modelului folosesc internet, dacă lipsesc componentele.

AI-ul poate greși, chiar dacă folosește fragmente din sursă. Verifică informațiile importante. Testează mai întâi pe fișiere demonstrative.
