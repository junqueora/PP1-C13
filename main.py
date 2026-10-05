"""Ponto de entrada: abre a interface do projeto.

Execute a partir da raiz do projeto:  python main.py
"""
import sys

from PyQt5.QtWidgets import QApplication

from gui.janela_principal import JanelaPrincipal


def main():
    app = QApplication(sys.argv)
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
