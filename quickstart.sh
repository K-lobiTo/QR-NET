#!/bin/bash
# QR-NET File Transfer — Quick Start

# Este script configura y ejecuta una transferencia de prueba entre dos máquinas

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Verificar dependencias
check_dependencies() {
    print_header "Verificando dependencias"

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 no encontrado"
        exit 1
    fi
    print_success "Python 3 encontrado: $(python3 --version)"

    if ! python3 -c "import cv2" 2>/dev/null; then
        print_error "OpenCV no instalado"
        exit 1
    fi
    print_success "OpenCV instalado"

    if ! python3 -c "import qrcode" 2>/dev/null; then
        print_error "qrcode no instalado"
        exit 1
    fi
    print_success "qrcode instalado"
}

# Activar venv
activate_venv() {
    print_header "Activando entorno virtual"

    if [ ! -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        print_error "Entorno virtual no encontrado"
        print_info "Ejecutar:"
        echo "  cd $PROJECT_ROOT"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi

    source "$PROJECT_ROOT/venv/bin/activate"
    print_success "Entorno virtual activado"
}

# Crear archivo de prueba
create_test_file() {
    print_header "Creando archivo de prueba"

    TEST_FILE="$SRC_DIR/test_upload.bin"

    # Crear archivo de 1 MB con datos aleatorios
    dd if=/dev/urandom of="$TEST_FILE" bs=1M count=1 2>/dev/null

    print_success "Archivo de prueba creado: $TEST_FILE"
    echo "  Tamaño: $(du -h "$TEST_FILE" | cut -f1)"
}

# Modo receptor
run_receiver() {
    print_header "Modo Receptor"

    echo -e "\nEscucha en el puerto 9000 aguardando archivos...\n"
    echo "Ejecutando con: python3 receiver.py $@"
    echo ""

    cd "$SRC_DIR"
    python3 receiver.py "$@"
}

# Modo emisor
run_sender() {
    print_header "Modo Emisor"

    if [ $# -lt 1 ]; then
        print_error "Uso: $0 send <archivo>"
        echo ""
        echo "Ejemplo:"
        echo "  $0 send documento.pdf"
        exit 1
    fi

    FILE="$1"

    if [ ! -f "$FILE" ]; then
        print_error "Archivo no encontrado: $FILE"
        exit 1
    fi

    print_header "Modo Emisor"
    echo -e "\nEnviando archivo...\n"
    echo "Archivo: $FILE"
    echo ""

    cd "$SRC_DIR"
    python3 sender.py "$FILE"
}

# Modo demostración
run_demo() {
    print_header "Modo Demostración"

    create_test_file

    print_info "Este modo ejecutará una transferencia de demostración"
    print_info "Se requieren:"
    print_info "  1. Una cámara en la máquina receptora"
    print_info "  2. El emisor debe tener visibilidad de la pantalla"
    echo ""
    read -p "¿Continuar? (s/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi

    read -p "¿Eres quien RECIBE (r) o ENVÍA (e) el archivo? (r/e) " role
    echo ""

    if [[ $role =~ ^[Rr]$ ]]; then
        read -p "Ingresa el índice de tu cámara (ej: 0): " camera_index
        run_receiver --camera "$camera_index"
    else
        run_sender "test_upload.bin"
    fi
}

# Mostrar ayuda
show_help() {
    print_header "QR-NET File Transfer — Quick Start"

    cat << 'EOF'

COMANDOS:

  ./quickstart.sh check
      Verifica que todas las dependencias estén instaladas

  ./quickstart.sh receive [--camera CAM]
      Inicia como receptor (captura QRs por cámara)
      Ejemplo: ./quickstart.sh receive --camera 0

  ./quickstart.sh send <archivo>
      Inicia como emisor (envía un archivo via QR)
      Ejemplo: ./quickstart.sh send documento.pdf

  ./quickstart.sh demo
      Ejecuta demostración interactiva

  ./quickstart.sh help
      Muestra esta ayuda

EJEMPLOS DE TRANSFERENCIA:

  Machine A (Receptor):
    $ ./quickstart.sh receive --camera 0

  Machine B (Emisor):
    $ ./quickstart.sh send documento.pdf

CONFIGURACIÓN:

  Puerto predeterminado: 9000
  Cámara predeterminada: 0
  Timeout: 300 segundos

DOCUMENTACIÓN:

  Ver docs/FILE_TRANSFER.md para documentación completa

EOF
}

# Main
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    case "$1" in
        check)
            activate_venv
            check_dependencies
            print_success "Todas las dependencias instaladas correctamente"
            ;;
        receive)
            activate_venv
            shift
            run_receiver "$@"
            ;;
        send)
            activate_venv
            shift
            run_sender "$@"
            ;;
        demo)
            activate_venv
            check_dependencies
            run_demo
            ;;
        help)
            show_help
            ;;
        *)
            print_error "Comando desconocido: $1"
            echo "Ejecuta: $0 help"
            exit 1
            ;;
    esac
}

main "$@"
