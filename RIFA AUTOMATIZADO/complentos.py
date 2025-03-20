    f' Soporte: Envíanos tus Recomendaciones y Errores 🚀\n\nCódigo de contacto:\n\n/{cid}\n\n'\
    f'visite nuestra página de Facebook:\n\n/Soporte'


@bot.message_handler(commands=['Soporte'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'https://www.facebook.com/permalink.php?story_fbid=453345640577241&id=100077054252925&ref=embed_post'
    bot.send_message(chat_id, respuesta)    


@bot.message_handler(commands=['Invertir'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'https://t.me/Invertir_bot'
    bot.send_message(chat_id, respuesta)

@bot.message_handler(commands=['publicidad'])
def handle_verificar_rifa_command(message):
    chat_id = message.chat.id
    respuesta = 'https://t.me/QRpublicidad_bot'
    bot.send_message(chat_id, respuesta)    

    bot.send_message(chat_id, "visite nuestra página de Facebook de soporte:\n\n/Soporte\n\n")
    bot.send_message(chat_id, "/Invertir: Descubre oportunidades de inversión rentables. 💼💰\n\n")
    bot.send_message(chat_id, "/publicidad: Ofrezco trabajo a cambio de visitas o publicidad para mi aplicación.\n\n" )   
                     
                   "visite nuestra página de Facebook de soporte:\n\n/Soporte\n\n"\

           "Ayuda - Cualquier error que presente y ya pagó y no le llega su boleto, por favor, visite nuestra página de Facebook de soporte:\n\n/Soporte\n\n" \

                       "/Invertir: Descubre oportunidades de inversión rentables. 💼💰\n\n"\
            "/publicidad: Ofrezco trabajo a cambio de visitas o publicidad para mi aplicación.\n\n"
                               
