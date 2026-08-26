import os
from imap_tools import MailBox, AND
from config.settings import Settings

def buscar_arquivos_email():
    """
    Busca o ÚLTIMO e-mail que contenha 'Plena' no assunto
    e baixa os anexos Excel (.xlsx) para a pasta 'imports'.
    """
    arquivos_baixados = []
    
    if not Settings.GMAIL_USER or not Settings.GMAIL_PASS:
        print("❌ Erro: GMAIL_USER ou GMAIL_PASS não configurados no .env")
        return arquivos_baixados

    # Termo de busca simplificado: lido do .env via Settings

    try:
        print(f"🔄 Conectando ao Gmail: {Settings.GMAIL_USER}")
        
        with MailBox(Settings.IMAP_SERVER).login(Settings.GMAIL_USER, Settings.GMAIL_PASS) as mailbox:
            
            # Busca por e-mails NÃO LIDOS (UNSEEN) com "Plena" no assunto
            for msg in mailbox.fetch(AND(seen=False, subject=Settings.TERMO_BUSCA_IMAP)):
                
                print(f"📩 Novo e-mail detectado: {msg.subject} (Data: {msg.date_str})")
                
                for att in msg.attachments:
                    if att.filename.lower().endswith('.xlsx'):
                        caminho_local = os.path.join(Settings.IMPORTS_DIR, att.filename)
                        
                        print(f"⬇️ Baixando anexo: {att.filename}")
                        
                        with open(caminho_local, 'wb') as f:
                            f.write(att.payload)
                        
                        arquivos_baixados.append(caminho_local)
            
            if not arquivos_baixados:
                # print(f"ℹ️ Sem novos e-mails 'Plena' com anexos Excel.")
                pass
            else:
                print(f"✅ Sincronização finalizada: {len(arquivos_baixados)} novo(s) arquivo(s) baixado(s).")

        return arquivos_baixados

    except Exception as e:
        print(f"❌ Erro na busca simplificada por e-mail [Plena]: {e}")
        return arquivos_baixados
