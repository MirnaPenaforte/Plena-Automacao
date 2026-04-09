import os
import shutil
import glob
from datetime import datetime, timedelta

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def arquivar_arquivos_importacao(diretorio_imports='imports'):
    """
    Cria uma rotina de backup de arquivos Excel (.xlsx) diários.
    Agrupa por 'Mês/Dia', guardando os arquivos originais.
    Limpa backups que tenham mais de um mês (exclui os mais antigos que 30 dias guardados).
    """
    try:
        hoje = datetime.now()
        mes_str = f"{hoje.month:02d}_{MESES_PT[hoje.month]}_{hoje.year}"
        dia_str = hoje.strftime('%d-%m-%Y')
        
        dir_backups = os.path.join(diretorio_imports, 'backups')
        dir_backup_mes = os.path.join(dir_backups, mes_str)
        dir_backup_dia = os.path.join(dir_backup_mes, dia_str)
        
        # Cria as pastas de backup (Mês e Dia)
        os.makedirs(dir_backup_dia, exist_ok=True)
        
        # Pega todos os Excel soltos dentro da pasta imports (apenas arquivos)
        # ignora os arquivos que já estão dentro de pastas (como /backups/)
        padrao_excel = os.path.join(diretorio_imports, '*.xlsx')
        excel_files = [f for f in glob.glob(padrao_excel) if os.path.isfile(f)]
        
        arquivos_copiados = []
        for arquivo in excel_files:
            nome_base, ext = os.path.splitext(os.path.basename(arquivo))
            # Registra o nome com dia e hora
            data_hora_str = hoje.strftime('%d-%m-%Y_%Hh%Mm')
            novo_nome = f"{nome_base}_{data_hora_str}{ext}"
            
            caminho_destino = os.path.join(dir_backup_dia, novo_nome)
            shutil.copy2(arquivo, caminho_destino)
            arquivos_copiados.append(caminho_destino)
            print(f"📦 Backup salvo: {novo_nome} em {mes_str}/{dia_str}")
                
        # Limpar os arquivos muito antigos (mais de 30 dias ou referentes a meses anteriores removíveis)
        limpar_backups_antigos(dir_backups, hoje)
        
        return arquivos_copiados

    except Exception as e:
        print(f"❌ Erro na rotina de backup dos arquivos de importação: {e}")
        return []


def limpar_backups_antigos(dir_backups, data_atual):
    """
    Remove as pastas de meses de backup que são muito antigas.
    Mantém o mês atual e o mês anterior ao atual. Exclui o resto para manter apenas o tempo necessário (aprox 30-60 dias).
    """
    if not os.path.exists(dir_backups):
        return
        
    for pasta_mes in os.listdir(dir_backups):
        caminho_pasta = os.path.join(dir_backups, pasta_mes)
        
        if os.path.isdir(caminho_pasta):
            # Formato esperado: 03_Marco_2026
            partes = pasta_mes.split('_')
            if len(partes) >= 3:
                try:
                    mes_pasta = int(partes[0])
                    ano_pasta = int(partes[-1])
                    
                    # Convertendo Mês + Ano num índice linear de meses para comparar a diferença
                    meses_atuais_total = data_atual.year * 12 + data_atual.month
                    meses_pasta_total = ano_pasta * 12 + mes_pasta
                    
                    # Se o índice da pasta é menor do que (mês atual - 1), excluímos (arquivos guardados têm mais de ~30 dias)
                    if meses_atuais_total - meses_pasta_total >= 2:
                        shutil.rmtree(caminho_pasta)
                        print(f"🧹 Backup de mês antigo deletado (substituído): {pasta_mes}")
                except Exception as e:
                    print(f"⚠️ Erro ao verificar idade do backup na pasta {pasta_mes}: {e}")

