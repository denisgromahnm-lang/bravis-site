"""Optional wallet setup help beside the existing guest-card registration link."""
import html

# Android destination is the application used by Loona's public installApp flow.
# Apple Wallet identity is confirmed by Apple's public lookup (Apple Inc., com.apple.Passbook).
APPLE_WALLET_URL = 'https://apps.apple.com/app/id1160481993'
ANDROID_WALLET_URL = 'https://play.google.com/store/apps/details?id=io.walletpasses.android'


def render_wallet_help():
    h = lambda value: html.escape(value, quote=True)
    return f'''<details class="bravis-wallet-help">
<summary>Нет кошелька на телефоне?</summary>
<div class="bravis-wallet-help__body">
<p>Кошелёк хранит карту BRAVIS: её QR-код для официанта и баланс бонусов.</p>
<div class="bravis-wallet-help__links">
<a href="{h(APPLE_WALLET_URL)}" target="_blank" rel="noopener noreferrer"><span>iPhone</span><strong>Apple Wallet ↗</strong></a>
<a href="{h(ANDROID_WALLET_URL)}" target="_blank" rel="noopener noreferrer"><span>Android</span><strong>WalletPasses ↗</strong></a>
</div>
<p>На iPhone приложение Wallet обычно уже установлено. Если вы его удалили, восстановите по ссылке выше. На Android установите WalletPasses из Google Play.</p>
<ol><li>Установите кошелёк, если его ещё нет.</li><li>Вернитесь на эту страницу и нажмите кнопку оформления карты.</li><li>Пройдите оформление, сохраните карту BRAVIS в кошельке и покажите её QR-код официанту.</li></ol>
<p class="bravis-wallet-help__note">Установка кошелька — первый шаг. Затем нужно добавить в него саму карту BRAVIS. Если нужна помощь, обратитесь к сотруднику ресторана.</p>
</div></details>'''
