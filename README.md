🌐 **NyxNet - Auto Changer IP with Proxy**

This script is professional and fast IP, which shows your Real IP and Tor IP in real time, with automatic identity exchange using 

🚀 **Funcionalidades**

✔️ **Exibe IP Real (sem Tor).**
✔️ **Exibe IP via Tor (SOCKS5).**
✔️ **Troca de identidade automática (NEWNYM) via Tor ControlPort.**
✔️ **Atualização rápida e em tempo real (1s).**
✔️ **Interface colorida e responsiva com Rich.**
✔️ **Configuração simples e documentação completa.**


⚙️ **Requisitos**

**Python 3.8+**
| **Tor instalado e rodando no sistema**
| **Dependências Python listadas em requirements.txt:**

```bash
| **pip install -r requirements.txt**
```
🔧 **Configuração do Tor**

**Edite o arquivo de configuração do Tor (torrc) para habilitar o ControlPort**
**No Linux:**
```bash
| sudo nano /etc/tor/torrc
```
**Descomente (ou adicione):**
```bash
| ControlPort 9051
| CookieAuthentication 1
```
**Reinicie o Tor:**
```bash
| sudo systemctl restart tor
```

**Verifique se está rodando:**
```bash
| netstat -tulnp | grep tor
```
**Você deve ver algo como:**
```bash
127.0.0.1:9050  (SOCKS)
127.0.0.1:9051  (ControlPort)
```

---

## 🚀 Instalação
Clone o repositório e instale as dependências:  

```bash
git clone https://github.com/0xBl4ckn3t/NyxNet.git
cd NyxNet
pip install -r requirements.txt
