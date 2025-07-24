async def update_user_state(user_id, state):
    """Update the user's current state in the psychology test"""
    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute(
            "UPDATE users SET current_state = %s WHERE user_id = %s",
            (state, user_id)
        )
    await conn.commit()
    return True

async def get_user_state(user_id):
    """Get the user's current state in the psychology test"""
    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT current_state FROM users WHERE user_id = %s",
            (user_id,)
        )
        result = await cursor.fetchone()
    
    if result and result[0]:
        return result[0]
    return "NONE"

async def save_test_response(user_id, question_key, answer):
    """Save user's response to a test question"""
    conn = await get_connection()
    async with conn.cursor() as cursor:
        # Check if response exists
        await cursor.execute(
            "SELECT id FROM test_responses WHERE user_id = %s AND question_key = %s",
            (user_id, question_key)
        )
        result = await cursor.fetchone()
        
        if result:
            # Update existing response
            await cursor.execute(
                "UPDATE test_responses SET answer = %s WHERE user_id = %s AND question_key = %s",
                (answer, user_id, question_key)
            )
        else:
            # Insert new response
            await cursor.execute(
                "INSERT INTO test_responses (user_id, question_key, answer) VALUES (%s, %s, %s)",
                (user_id, question_key, answer)
            )
    await conn.commit()
    return True