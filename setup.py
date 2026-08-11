#!/usr/bin/env python
"""
MAGI System Setup Script
Configura o ambiente inicial do projeto
"""

import os
import sys
import shutil
from pathlib import Path


def print_header(text: str):
    """Imprime header formatado"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_success(text: str):
    """Imprime mensagem de sucesso"""
    print(f"✅ {text}")


def print_error(text: str):
    """Imprime mensagem de erro"""
    print(f"❌ {text}")


def print_warning(text: str):
    """Imprime aviso"""
    print(f"⚠️  {text}")


def print_info(text: str):
    """Imprime informação"""
    print(f"ℹ️  {text}")


def check_python_version():
    """Verifica versão do Python"""
    print_header("Verificando Versão do Python")

    required_version = (3, 11)
    current_version = sys.version_info[:2]

    if current_version >= required_version:
        print_success(f"Python {current_version[0]}.{current_version[1]} detectado")
        return True
    else:
        print_error(f"Python {required_version[0]}.{required_version[1]}+ requerido")
        print_info(f"Versão atual: {current_version[0]}.{current_version[1]}")
        return False


def check_virtual_environment():
    """Verifica se está em ambiente virtual"""
    print_header("Verificando Ambiente Virtual")

    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print_success("Ambiente virtual ativo")
        print_info(f"Localização: {sys.prefix}")
        return True
    else:
        print_warning("Nenhum ambiente virtual ativo")
        print_info("Recomendado: python -m venv venv && source venv/bin/activate")
        return False


def create_env_file():
    """Cria arquivo .env a partir de .env.example"""
    print_header("Configurando Variáveis de Ambiente")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print_warning(".env já existe")
        return True

    if not env_example.exists():
        print_error(".env.example não encontrado")
        return False

    # Copiar .env.example para .env
    shutil.copy(env_example, env_file)
    print_success(".env criado a partir de .env.example")

    # Avisar sobre preenchimento
    print_warning("⚠️  Por favor, configure suas API keys em .env:")
    print_info("  CLAUDE_API_KEY=sua_chave_aqui")
    print_info("  GEMINI_API_KEY=sua_chave_aqui")
    print_info("  GROQ_API_KEY=sua_chave_aqui")

    return True


def install_dependencies():
    """Instala dependências Python"""
    print_header("Instalando Dependências")

    requirements_file = Path("requirements.txt")

    if not requirements_file.exists():
        print_error("requirements.txt não encontrado")
        return False

    import subprocess

    try:
        print_info("Executando: pip install -r requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print_success("Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao instalar dependências: {e}")
        return False


def verify_installation():
    """Verifica se tudo foi instalado corretamente"""
    print_header("Verificando Instalação")

    required_modules = [
        "anthropic",
        "google.genai",
        "groq",
        "rich",
    ]

    all_available = True
    for module_name in required_modules:
        try:
            __import__(module_name)
            print_success(f"Módulo '{module_name}' disponível")
        except ImportError:
            print_error(f"Módulo '{module_name}' não encontrado")
            all_available = False

    return all_available


def print_next_steps():
    """Imprime próximos passos"""
    print_header("Próximos Passos")

    print("1. Configure suas API keys no arquivo .env:")
    print_info("   • Gemini: https://makersuite.google.com/app/apikey")
    print_info("   • Groq (gratuito): https://console.groq.com/")
    print_info("   • Claude: https://console.anthropic.com/")

    print("\n2. Teste o sistema em modo interativo:")
    print_info("   python cli.py")

    print("\n3. Execute exemplos avançados:")
    print_info("   python example_advanced_usage.py")

    print("\n4. Execute testes:")
    print_info("   pytest test_magi.py -v")

    print("\n5. Leia a documentação:")
    print_info("   • README.md - Documentação principal")
    print_info("   • DEVELOPMENT.md - Guia de desenvolvimento")


def main():
    """Executa setup completo"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "   🚀 MAGI SYSTEM SETUP - Multi-Agent AI Governance Interface".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    steps_passed = 0
    steps_total = 5

    # Step 1: Check Python
    if check_python_version():
        steps_passed += 1
    else:
        print_error("Setup abortado: versão Python incompatível")
        return False

    # Step 2: Check Virtual Environment
    check_virtual_environment()  # Apenas aviso, não bloqueia
    steps_passed += 1

    # Step 3: Create .env
    if create_env_file():
        steps_passed += 1
    else:
        print_warning("Pulando criação de .env")

    # Step 4: Install Dependencies
    if install_dependencies():
        steps_passed += 1
    else:
        print_error("Falha ao instalar dependências")
        return False

    # Step 5: Verify Installation
    if verify_installation():
        steps_passed += 1
    else:
        print_warning("Alguns módulos podem não estar disponíveis")

    # Summary
    print_header(f"Setup Completo - {steps_passed}/{steps_total} Etapas")

    if steps_passed >= 4:
        print_success("✨ Ambiente MAGI configurado com sucesso!")
        print_next_steps()
        return True
    else:
        print_error("Setup incompleto - revise os erros acima")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
