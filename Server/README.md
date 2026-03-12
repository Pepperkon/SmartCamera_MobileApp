1. **Ustawienie adresu IP (tylko raz):**

Po pierwszym pobraniu, stwórz plik .env w folderze Server. W nim wpisz swój adres IP, przykład:

```bash
IP='192.168.0.59'
```

Dzięki temu już nigdy nie trzeba będzie go zmieniać. W części SmartCam jeszcze nie zostało to wprowadzone, więc tam trzeba zmienić pliki w folderze **services**

2. **Instalacja uv (tylko raz):**

- **Linux/WSL**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- **Windows**:
    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

3. **Przygotowanie środowiska (zawsze po git pull w folderze Server):**

```bash
uv sync
```

Ta jedna komenda zrobi wszystko za Ciebie:

- Pobierze odpowiednią wersję Pythona.
- Stworzy wirtualne środowisko .venv.
- Zainstaluje wszystkie biblioteki z pliku pyproject.toml.

4. **Uruchamianie serwera:**

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```
Hot Reload:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Jak dodać nową bibliotekę?

```bash
uv add nazwa_paczki
```
