import os
import json
from openai import OpenAI

# --- Setup ---
# It's recommended to use a .env file and load the key via a config file.
# For this example, ensure the OPENAI_API_KEY is set as an environment variable.
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except TypeError:
    print("🚨 OPENAI_API_KEY environment variable is not set.")
    client = None

class QuestAnalyzerAgent:
    """
    Analyzes quest text to produce objective base reward values by breaking down
    the quest into multiple dimensions.
    """
    def __init__(self):
        """Initializes the agent and creates a cache for storing results."""
        self._cache = {}

    def run(self, quest_text: str) -> tuple[dict[str, int] | None, dict[str, int] | str]:
        """
        Analyzes the given quest text and returns the calculated rewards and the
        raw analysis data from the LLM.

        Args:
            quest_text (str): The assignment text provided by the teacher.

        Returns:
            A tuple containing:
            - A dictionary with the final calculated rewards {'exploration_data', 'coral'}.
            - A dictionary with the raw analysis scores from the LLM.
            Returns (None, "Error Message") on failure.
        """
        # 1. Check cache for previous analysis
        if quest_text in self._cache:
            print("✅ (Responding from cache)")
            return self._cache[quest_text]


        if not client:
            raise EnvironmentError("OpenAI client is not initialized. Check your API key.")

        prompt = f"""
        You are an expert instructional designer who analyzes educational tasks
        by breaking them down into core components. Analyze the following quest text
        and evaluate the 4 key metrics that will be used to calculate 'Exploration Data'
        for student growth and 'Coral' for activity rewards.

        Quest Text: "{quest_text}"

        Rate each metric on an integer scale from 1 to 10.
        You MUST respond ONLY in the following JSON format. Do not add any other explanations.

        {{
          "conceptual_difficulty": <Score for conceptual understanding and application>,
          "time_effort": <Score for the absolute time and effort required>,
          "creativity_required": <Score for the need for original or creative output>,
          "repetitiveness": <Score for the amount of simple memorization or repetitive tasks>
        }}
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0, 
            )

            # 3. Parse the multi-dimensional analysis from the LLM
            llm_analysis = json.loads(response.choices[0].message.content)

            # 4. Calculate final rewards using weighted formulas
            # These formulas can be easily adjusted later to balance the game economy.
            rewards = {}
            rewards['exploration_data'] = (llm_analysis.get("conceptual_difficulty", 0) * 5) + \
                                          (llm_analysis.get("creativity_required", 0) * 3) + \
                                          (llm_analysis.get("time_effort", 0) * 2)

            rewards['coral'] = (llm_analysis.get("time_effort", 0) * 4) + \
                               (llm_analysis.get("repetitiveness", 0) * 2)

            # 5. Cache and return the results
            self._cache[quest_text] = (rewards, llm_analysis)
            print("✅ (Responding from API)")
            return rewards, llm_analysis

        except json.JSONDecodeError:
            error_msg = f"LLM response parsing failed: {response.choices[0].message.content}"
            print(f"🚨 {error_msg}")
            return None, error_msg
        except (KeyError, TypeError) as e:
            error_msg = f"LLM response key error: {e}. Response: {response.choices[0].message.content}"
            print(f"🚨 {error_msg}")
            return None, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during the API call: {e}"
            print(f"🚨 {error_msg}")
            return None, error_msg

# --- Usage Example ---
if __name__ == '__main__':
    if not client:
        print("❗️ Please set your API key to run the example.")
    else:
        quest_analyzer = QuestAnalyzerAgent()

        quests = [
            "수학의 정석 1단원 연습문제 10개 풀기"
        ]

        for q in quests:
            print(f"\n--- Analyzing Quest: \"{q}\" ---")
            final_rewards, raw_analysis = quest_analyzer.run(q)

            if final_rewards:
                print("📊 LLM 분석 결과:")
                for key, value in raw_analysis.items():
                    print(f"   - {key.replace('_', ' ').title()}: {value}")
                
                print("\n💰 Calculated Rewards:")
                print(f"   - 탐사 데이터 (Exploration Data): {final_rewards['exploration_data']}")
                print(f"   - 코랄 (Coral): {final_rewards['coral']}")