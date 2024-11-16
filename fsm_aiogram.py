import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage, Redis
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from dotenv import load_dotenv
from typing import Dict, Union

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

redis = Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)))

storage = RedisStorage(redis=redis)

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Создаем "базу данных" пользователей
user_dict: dict[int, Dict[str, Union[str, int, bool]]] = {}


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    fill_name = State()        # Состояние ожидания ввода имени
    fill_age = State()         # Состояние ожидания ввода возраста
    fill_gender = State()      # Состояние ожидания выбора пола
    upload_photo = State()     # Состояние ожидания загрузки фото
    fill_education = State()   # Состояние ожидания выбора образования
    fill_wish_news = State()   # Состояние ожидания выбора получать ли новости


@dp.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    logger.info(f"User {message.from_user.id} started the bot.")
    await message.answer(
        text='Этот бот демонстрирует работу FSM\n\n'
             'Чтобы перейти к заполнению анкеты - '
             'отправьте команду /fillform'
    )


@dp.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    logger.info(f"User {message.from_user.id} tried to cancel, but is not in any state.")
    await message.answer(
        text='Отменять нечего. Вы вне машины состояний\n\n'
             'Чтобы перейти к заполнению анкеты - '
             'отправьте команду /fillform'
    )


@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} canceled the process.")
    await message.answer(
        text='Вы вышли из машины состояний\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'отправьте команду /fillform'
    )
    await state.clear()


@dp.message(Command(commands='fillform'), StateFilter(default_state))
async def process_fillform_command(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} initiated filling the form.")
    await message.answer(text='Пожалуйста, введите ваше имя')
    await state.set_state(FSMFillForm.fill_name)


@dp.message(StateFilter(FSMFillForm.fill_name), F.text.isalpha())
async def process_name_sent(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} entered name: {message.text}")
    await state.update_data(name=message.text)
    await message.answer(text='Спасибо!\n\nА теперь введите ваш возраст')
    await state.set_state(FSMFillForm.fill_age)


@dp.message(StateFilter(FSMFillForm.fill_name))
async def warning_not_name(message: Message):
    logger.warning(f"User {message.from_user.id} entered invalid name: {message.text}")
    await message.answer(
        text='То, что вы отправили не похоже на имя\n\n'
             'Пожалуйста, введите ваше имя\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )


@dp.message(StateFilter(FSMFillForm.fill_age),
            lambda x: x.text.isdigit() and 4 <= int(x.text) <= 120)
async def process_age_sent(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} entered age: {message.text}")
    await state.update_data(age=message.text)
    male_button = InlineKeyboardButton(
        text='Мужской ♂',
        callback_data='male'
    )
    female_button = InlineKeyboardButton(
        text='Женский ♀',
        callback_data='female'
    )
    undefined_button = InlineKeyboardButton(
        text='🤷 Пока не ясно',
        callback_data='undefined_gender'
    )
    keyboard: list[list[InlineKeyboardButton]] = [
        [male_button, female_button],
        [undefined_button]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        text='Спасибо!\n\nУкажите ваш пол',
        reply_markup=markup
    )
    await state.set_state(FSMFillForm.fill_gender)


@dp.message(StateFilter(FSMFillForm.fill_age))
async def warning_not_age(message: Message):
    logger.warning(f"User {message.from_user.id} entered invalid age: {message.text}")
    await message.answer(
        text='Возраст должен быть целым числом от 4 до 120\n\n'
             'Попробуйте еще раз\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


@dp.callback_query(StateFilter(FSMFillForm.fill_gender),
                   F.data.in_(['male', 'female', 'undefined_gender']))
async def process_gender_press(callback: CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} selected gender: {callback.data}")
    await state.update_data(gender=callback.data)
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь загрузите, пожалуйста, ваше фото'
    )
    await state.set_state(FSMFillForm.upload_photo)


@dp.message(StateFilter(FSMFillForm.fill_gender))
async def warning_not_gender(message: Message):
    logger.warning(f"User {message.from_user.id} entered invalid gender selection.")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе пола\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


@dp.message(StateFilter(FSMFillForm.upload_photo),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):
    logger.info(f"User {message.from_user.id} uploaded photo with id: {largest_photo.file_id}")
    await state.update_data(
        photo_unique_id=largest_photo.file_unique_id,
        photo_id=largest_photo.file_id
    )
    secondary_button = InlineKeyboardButton(
        text='Среднее',
        callback_data='secondary'
    )
    higher_button = InlineKeyboardButton(
        text='Высшее',
        callback_data='higher'
    )
    no_edu_button = InlineKeyboardButton(
        text='🤷 Нету',
        callback_data='no_edu'
    )
    keyboard: list[list[InlineKeyboardButton]] = [
        [secondary_button, higher_button],
        [no_edu_button]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        text='Спасибо!\n\nУкажите ваше образование',
        reply_markup=markup
    )
    await state.set_state(FSMFillForm.fill_education)


@dp.message(StateFilter(FSMFillForm.upload_photo))
async def warning_not_photo(message: Message):
    logger.warning(f"User {message.from_user.id} sent an invalid photo.")
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


@dp.callback_query(StateFilter(FSMFillForm.fill_education),
                   F.data.in_(['secondary', 'higher', 'no_edu']))
async def process_education_press(callback: CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} selected education: {callback.data}")
    await state.update_data(education=callback.data)
    yes_news_button = InlineKeyboardButton(
        text='Да',
        callback_data='yes_news'
    )
    no_news_button = InlineKeyboardButton(
        text='Нет, спасибо',
        callback_data='no_news')
    keyboard: list[list[InlineKeyboardButton]] = [
        [yes_news_button, no_news_button]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(
        text='Спасибо!\n\nОстался последний шаг.\n'
             'Хотели бы вы получать новости?',
        reply_markup=markup
    )
    await state.set_state(FSMFillForm.fill_wish_news)


@dp.callback_query(StateFilter(FSMFillForm.fill_education),
                   F.data.in_(['secondary', 'higher', 'no_edu']))
async def warning_not_education(callback: CallbackQuery):
    logger.warning(f"User {callback.from_user.id} made an invalid education selection.")
    await callback.message.answer(
        text='Пожалуйста, пользуйтесь кнопками для выбора образования'
    )


@dp.callback_query(StateFilter(FSMFillForm.fill_wish_news), F.data.in_(['yes_news', 'no_news']))
async def process_wish_news_press(callback: CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} selected news preference: {callback.data}")
    await state.update_data(wish_news=callback.data)
    await callback.message.delete()
    user_data = await state.get_data()
    user_dict[callback.from_user.id] = user_data
    await callback.message.answer(
        text=f'Анкета заполнена!\n\n'
             f'Ваши данные:\n\n'
             f'Имя: {user_data["name"]}\n'
             f'Возраст: {user_data["age"]}\n'
             f'Пол: {user_data["gender"]}\n'
             f'Фото:'
    )
    await callback.message.answer_photo(user_data["photo_id"])
    await callback.message.answer(
        text=f'Образование: {user_data["education"]}\n'
             f'Получать новости: {user_data["wish_news"]}'
    )
    await state.clear()



@dp.callback_query(StateFilter(FSMFillForm.fill_wish_news))
async def warning_not_wish_news(callback: CallbackQuery):
    logger.warning(f"User {callback.from_user.id} made an invalid news preference selection.")
    await callback.message.answer(
        text='Пожалуйста, выберите, хотите ли вы получать новости'
    )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
               "[%(asctime)s] - %(name)s - %(message)s"
    )

    logger.info("Starting bot...")
    dp.run_polling(bot)
