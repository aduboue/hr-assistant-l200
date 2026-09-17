# HR Assistant Demo Playbook

**Presenter Setup:**

- Ensure the agent environment is running.

- Ensure the agent code is loaded with the internal JSON mock data.

### Step 1: Ingestion & Initial Synthesis

**Narrative:** The CHRO needs a quick health check on the quarter.

- **Presenter Action:** Start the chat interaction.

- **Copy & Paste Prompt 1:**

  > Hi, please analyze the Q3 HR stats from our internal dataset 'SAMPLE_HR_DATA' and give me a high-level executive summary of our overall performance. Focus on headcount growth, employee NPS, and engagement scores.

- **Expected Agent Output:** The agent should provide a brief summary noting the 5% headcount growth and stable NPS (75), but _crucially_, it will proactively flag the deteriorating Status of the Sales Department based on the internal JSON data.

### Step 2: Proactive Anomaly Detection

**Narrative:** The CHRO picks up on the agent's proactive alert and wants to see the data behind it.

- **Presenter Action:** Continue the chat.

- **Copy & Paste Prompt 2:**

  > You mentioned a deterioration in Sales. Can you break down the attrition trend over the last 3 quarters for me? Is it driven by time-to-fill or offer acceptance?

- **Expected Agent Output:** The agent will reference the department data for Sales. It will present the Attrition Rate climbing (Q1: 10.0%, Q2: 15.5%, Q3: 20.5%) and correctly identify that offer acceptance is flat (80%) while time-to-fill is driving the deterioration (climbing from 30 days to 60 days).

### Step 3: Deep-Dive Investigation via Internal Connectors

**Narrative:** Knowing _what_ is happening isn't enough; the CHRO needs to know _why_. We now demonstrate the agent's ability to cross-reference HR stats with operational databases and ATS systems.

- **Presenter Action:** Ask the agent to investigate using its tools.

- **Copy & Paste Prompt 3:**

  > This attrition trend in Sales is unacceptable. I need you to investigate the root cause. Please use your Employee_Database_Connector to check our ATS and Workday data for the Sales department. Are we seeing an issue with exit volume or top performer loss?

- **Expected Agent Output:** The agent will trigger the `employee_database_connector`. It will report back the mocked findings:
  - Exit volume is stable overall.

  - Top performer loss has spiked by +15.4%.

  - Root causes identified: Compensation lag vs market, strict RTO mandate driving attrition to remote-first competitors.

### Step 4: Remediation Strategy & Memo Generation

**Narrative:** The CHRO now has the full picture and needs to present this to the Executive Committee (Comex) along with a plan of action.

- **Presenter Action:** Ask for actionable insights and document generation.

- **Copy & Paste Prompt 4:**

  > Understood. Based on these root causes, what are your recommendations to correct this trajectory? Finally, draft a formal strategic memo for the Comex summarizing this Sales attrition issue, the root causes, and your proposed remediation strategy.

- **Expected Agent Output:**
  - The agent will generate strategic recommendations (e.g., targeted compensation bumps, relaxing the RTO mandate for Sales).

  - It will then trigger the `generate_memo_tool` and output a formal, structured preview of the Comex memo, demonstrating its ability to synthesize the entire investigation into an executive-ready format.
