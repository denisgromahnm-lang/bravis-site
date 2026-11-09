"""Guest-facing banquet facts; no customer data or unconfirmed package prices."""
from html import escape
import json
from pathlib import Path


def load_banquet_info(path):
    data = json.loads(Path(path).read_text(encoding='utf8'))
    capacity = data['capacity']
    seats = [capacity['banquetHall'], *capacity['otherHalls']]
    if (len(seats) != 3 or any(type(value) is not int or value <= 0 for value in seats)
            or sum(seats) != capacity['seatedTotal']):
        raise ValueError('Banquet room capacities must match the verified total')
    if type(data['corkagePerBottleRub']) is not int or data['corkagePerBottleRub'] <= 0:
        raise ValueError('A verified corkage amount is required')
    return data


def capacity_notice(data):
    capacity = data['capacity']
    return (f'<p class="banquet-capacity"><strong>До {capacity["seatedTotal"]} гостей</strong>'
            '<span>Три зала для ваших встреч. Рассадку и использование залов согласуем под ваш формат.</span></p>')


def banquet_questions(data):
    capacity = data['capacity']
    questions = [
        ('Сколько гостей можно пригласить?',
         f'В ресторане {capacity["seatedTotal"]} посадочных мест в трёх залах: банкетный зал — до {capacity["banquetHall"]} гостей, '
         f'два других зала — до {capacity["otherHalls"][0]} и {capacity["otherHalls"][1]} гостей. '
         'Рассадку, использование залов и доступность на вашу дату подтвердим при обсуждении мероприятия.'),
        ('Как получить расчёт стоимости?',
         'Напишите дату, число гостей, повод и ориентир по бюджету. Подберём меню и отдельно обсудим напитки, '
         'обслуживание и дополнительные услуги. Состав предложения и итоговые условия согласуем до подтверждения мероприятия.'),
        ('Можно со своим алкоголем?',
         f'Пробковый сбор — {data["corkagePerBottleRub"]} ₽ с бутылки. Напитки и количество бутылок обсудим при согласовании банкета.'),
        ('Какая предоплата и когда окончательный расчёт?',
         'Размер предоплаты согласуем под выбранное меню и условия мероприятия. '
         'Окончательный расчёт — в день проведения, после банкета, с учётом дополнительных заказов.'),
        ('Есть оборудование для музыки и презентаций?',
         'В ресторане есть телевизор, колонки, микшерный пульт и многоканальная аудиосистема. '
         'Возможны подключения через AUX, Bluetooth и флешку. Нужное оборудование, подключение и стоимость использования согласуем заранее.'),
        ('Можно заказать музыкантов, сомелье или аниматора?',
         'По запросу обсудим музыкальную программу, сомелье или аниматора для вашего события. '
         'Это дополнительные услуги: программу, доступность исполнителей и стоимость согласуем отдельно.'),
    ]
    cards = ''.join(f'<details><summary>{escape(title)}</summary><p>{escape(answer)}</p></details>' for title, answer in questions)
    return ('<section class="section banquet-faq" id="banquet-questions" aria-labelledby="banquet-questions-title">'
            '<div class="wrap"><div class="section-label"><span class="line"></span> ПЕРЕД ВАШИМ СОБЫТИЕМ</div>'
            '<h2 id="banquet-questions-title">Важные <em>детали.</em></h2>'
            f'<div class="banquet-faq__items">{cards}</div></div></section>')
