#!/bin/bash
# Assina o Papory com um certificado criado NESTE Mac, para o macOS lembrar as permissões
# (Microfone, Monitoramento de Entrada e Acessibilidade) quando o Papory for atualizado.
#
#   bash /Applications/Papory.app/Contents/Resources/assinar-papory.sh
#   bash assinar-papory.sh /outro/caminho/Papory.app
#
# Rode de novo depois de cada atualização do Papory. Usa só o que vem no macOS (openssl, security, codesign):
# não pede senha de administrador e não precisa das ferramentas de desenvolvedor da Apple.
# O certificado fica só neste Mac, em ~/Library/Application Support/Papory/assinatura. Apagar essa pasta desfaz tudo.
set -euo pipefail

APP="${1:-/Applications/Papory.app}"
APP="${APP%/}"
PASTA="$HOME/Library/Application Support/Papory/assinatura"
KC="$PASTA/papory-assinatura.keychain-db"
NOME="Papory (este Mac)"

if [ ! -d "$APP/Contents/MacOS" ]; then
  echo "Não achei o Papory em: $APP"
  echo "Arraste o Papory para a pasta Aplicativos, ou passe o caminho: bash $0 /caminho/do/Papory.app"
  exit 1
fi
if [ ! -w "$APP/Contents" ]; then
  echo "Sem permissão para alterar $APP. Apague o Papory de Aplicativos e arraste de novo a partir do .dmg."
  exit 1
fi

# Lista de chaveiros do usuário, sem o do Papory. O codesign só acha o certificado com o chaveiro do Papory
# na lista, então ele entra só durante a assinatura e a lista original volta no fim (mesmo se der erro).
LISTA=()
while IFS= read -r linha; do
  linha="${linha#"${linha%%[![:space:]]*}"}"
  linha="${linha#\"}"
  linha="${linha%\"}"
  case "$linha" in
    ""|*papory-assinatura.keychain-db) ;;
    *) LISTA+=("$linha") ;;
  esac
done < <(security list-keychains -d user)
tem_login=0
for k in "${LISTA[@]+"${LISTA[@]}"}"; do
  case "$k" in */login.keychain-db|*/login.keychain) [ -f "$k" ] && tem_login=1 ;; esac
done
if [ "$tem_login" != 1 ]; then
  echo "Não reconheci a lista de chaveiros deste Mac; para não mexer no que não devo, parei aqui."
  security list-keychains -d user
  exit 1
fi
devolver_lista() { security list-keychains -d user -s "${LISTA[@]}"; }

primeira_vez=0
if [ ! -f "$KC" ]; then
  primeira_vez=1
  echo "Criando o certificado deste Mac (só na primeira vez)..."
  mkdir -p "$PASTA"
  chmod 700 "$PASTA"
  SENHA="$(openssl rand -hex 16)"
  ( umask 077; printf '%s' "$SENHA" > "$PASTA/senha" )
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"; devolver_lista' EXIT
  cat > "$TMP/cert.cnf" <<FIM
[req]
distinguished_name = dn
prompt = no
x509_extensions = ext
[dn]
CN = $NOME
[ext]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
FIM
  openssl req -x509 -newkey rsa:2048 -sha256 -days 10950 -nodes -config "$TMP/cert.cnf" \
    -keyout "$TMP/chave.pem" -out "$TMP/cert.pem" 2>/dev/null
  openssl pkcs12 -export -inkey "$TMP/chave.pem" -in "$TMP/cert.pem" -name "$NOME" \
    -out "$TMP/cert.p12" -passout "pass:$SENHA"
  security create-keychain -p "$SENHA" "$KC"
  devolver_lista
  security set-keychain-settings "$KC"
  security unlock-keychain -p "$SENHA" "$KC"
  security import "$TMP/cert.p12" -k "$KC" -P "$SENHA" -T /usr/bin/codesign > /dev/null
  security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$SENHA" "$KC" > /dev/null
  rm -rf "$TMP"   # a chave em texto não fica no disco: daqui para frente só existe dentro do chaveiro
  trap - EXIT
fi

SENHA="$(cat "$PASTA/senha")"
security unlock-keychain -p "$SENHA" "$KC"

if pgrep -x Papory > /dev/null; then
  echo "Fechando o Papory..."
  pkill -x Papory || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do pgrep -x Papory > /dev/null || break; sleep 0.5; done
fi

echo "Assinando o Papory..."
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
trap 'devolver_lista' EXIT
security list-keychains -d user -s "${LISTA[@]}" "$KC"
codesign --force --deep --sign "$NOME" --keychain "$KC" "$APP"
devolver_lista
trap - EXIT
codesign --verify --deep --strict "$APP"
security lock-keychain "$KC"

echo
echo "Pronto: o Papory está assinado com o certificado deste Mac."
if [ "$primeira_vez" = 1 ]; then
  echo "Como é a primeira vez, libere as permissões UMA última vez:"
  echo "  em Privacidade e Segurança > Monitoramento de Entrada e > Acessibilidade, selecione o Papory,"
  echo "  clique no \"-\" para tirar da lista, abra o Papory e marque de novo quando ele pedir."
  echo "Daqui para frente, depois de cada atualização do Papory, é só rodar este comando de novo."
else
  echo "As permissões que você já deu continuam valendo."
fi
if [ -z "${PAPORY_SEM_ABRIR:-}" ]; then   # PAPORY_SEM_ABRIR=1: só assina, sem abrir (testes)
  open "$APP"
fi
