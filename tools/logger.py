from pathlib import Path
from datetime import datetime
import json
from langchain_core.messages import BaseMessage
import traceback
from typing import Dict, Any

def save_log_to_json(erro: Exception, state: Dict[str, Any]) -> None:
    """
    Salva os logs de erro em um arquivo JSON na pasta raiz do projeto.
    Garante a limpeza de objetos não serializáveis do estado antes de salvar.
    """
    try:
        root_dir = Path(__file__).resolve().parent.parent
        log_dir = root_dir / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        name_log = f"log_error_{datetime.now().strftime('%Y-%m-%d')}.json"
        filepath = log_dir / name_log

        # Limpeza no state pra não dar raise em not json serializable
        state_clean = {}
        for k, v in state.items():
            if isinstance(v, list):
                state_clean[k] = [m.content if isinstance(m, BaseMessage) else str(m) for m in v]
            else:
                state_clean[k] = v

        log_record = {
            "level": "ERROR",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "state": state_clean,
            "message": str(erro),
            "full_error": traceback.format_exc()
        }
        with open(filepath, 'a', encoding='utf-8') as f:
            json.dump(log_record, f, ensure_ascii=False)
            f.write('\n')
            
    except Exception as e:
        print(f"Erro ao salvar log: {e}")