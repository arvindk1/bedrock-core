from strands_agents import tool


@tool
def get_weather(city: str) -> str:
    """
    Retrieves current weather data.
    Args:
        city: The name of the city (e.g., 'Columbus')
    """
    # TODO: Replace with real weather API integration
    return f"The weather in {city} is sunny."


@tool
def get_crypto_price(ticker: str) -> str:
    """
    Fetches real-time cryptocurrency prices.
    Args:
        ticker: The crypto symbol (e.g., 'BTC')
    """
    # TODO: Replace with real crypto price API integration
    return f"The current price of {ticker} is $96,000."
