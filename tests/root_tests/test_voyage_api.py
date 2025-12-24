#!/usr/bin/env python3
"""Test Voyage AI API keys to verify they work correctly."""

import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_api_key(key_name, key_value):
    """Test a specific API key."""
    print(f"\nTesting {key_name}: {key_value[:10]}...")

    try:
        # Set the environment variable that voyageai expects
        os.environ["VOYAGE_API_KEY"] = key_value

        # Import voyageai after setting the key
        import voyageai

        # Create client
        client = voyageai.Client()

        # Test with a simple embedding
        result = client.embed(
            texts=["Test embedding"], model="voyage-code-3", input_type="document"
        )

        print(f"✅ {key_name} works! Embedding dimension: {len(result.embeddings[0])}")
        return True

    except Exception as e:
        print(f"❌ {key_name} failed: {str(e)}")
        return False


def main():
    """Test both API keys from .env file."""
    print("Testing Voyage AI API keys...")

    # Get both keys from environment
    key1 = os.getenv("VOYAGE_AI_API_KEY")
    key2 = os.getenv("VOYAGE_API_KEY")

    print(f"Found VOYAGE_AI_API_KEY: {key1[:10] if key1 else 'Not set'}...")
    print(f"Found VOYAGE_API_KEY: {key2[:10] if key2 else 'Not set'}...")

    # Test both keys
    success = False

    if key1:
        if test_api_key("VOYAGE_AI_API_KEY", key1):
            success = True
            print("\n✅ Use VOYAGE_API_KEY environment variable (not VOYAGE_AI_API_KEY)")

    if key2 and key2 != key1:
        if test_api_key("VOYAGE_API_KEY", key2):
            success = True

    if success:
        print("\n🎉 API key validation successful!")
        print("The voyageai library expects the VOYAGE_API_KEY environment variable.")
    else:
        print("\n❌ No working API key found.")
        print("Please check your API keys at https://dash.voyageai.com")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
