            mime="application/json",
        )

    st.divider()
    st.subheader("Rule-based laboratory extraction (comparison aid)")
    lab_rows = detect_lab_results(report_text)
    if lab_rows:
        rule_flagged = [row for row in lab_rows if row.get("Status") in {"Below stated range", "Above stated range"}]
        if rule_flagged:
            st.warning("Potential out-of-range values detected by the rule-based parser: " + "; ".join(f"{row.get('Parameter')} ({row.get('Status')})" for row in rule_flagged) + ". Check the original report carefully.")
        st.dataframe(lab_rows, use_container_width=True, hide_index=True)
        st.download_button(
            "Download recognized lab values (CSV)",
            data=csv_bytes(lab_rows),
            file_name="medical_report_results.csv",
            mime="text/csv",
        )
        st.caption("This parser supports a limited list of common test names. Value/range pairing can be wrong; verify every row against the source.")
    else:
        st.info("The built-in parser did not confidently identify any supported lab values. The AI section may still extract additional report content.")

    st.subheader("Rule-based report sections (fallback)")
    findings_raw = extract_section(report_text, ["Findings", "Observations"])
    impression_raw = extract_section(report_text, ["Impression", "Conclusion", "Conclusions", "Opinion", "Interpretation", "Diagnosis"])
    recommendations_raw = extract_section(report_text, ["Recommendation", "Recommendations", "Advice", "Suggestion", "Plan"])
    key_findings, normal_observations, recommendations = split_radiology_narrative(findings_raw, impression_raw, recommendations_raw)

    st.markdown("**Findings detected by rules**")
    if key_findings:
        for item in key_findings:
            st.write("• " + item)
    elif findings_raw or impression_raw:
        st.info("No separate main finding could be confidently separated from the extracted wording. Review the source text.")
    else:
        st.caption("No clear Findings or Impression heading detected.")

    st.markdown("**Normal / negative observations detected by rules**")
    if normal_observations:
        for item in normal_observations:
            st.write("• " + item)
    else:
        st.caption("No clearly worded normal or negative observations were separated.")

    st.markdown("**Recommendations detected by rules**")
    if recommendations:
        for item in recommendations:
            st.write("• " + item)
    else:
        st.caption("No separate recommendation was confidently detected.")

    explainers = explain_radiology(" ".join([findings_raw, impression_raw, recommendations_raw, *key_findings, *normal_observations, *recommendations]))
    if explainers:
        st.markdown("**Built-in term explanations**")
        for note in explainers:
            st.write("• " + note)

    st.warning(
        "For understanding only—not a diagnosis or treatment plan. This app analyzes the written report text, not the actual pixels of an X-ray, CT, or MRI. "
        "Do not delay urgent care because of an app summary. If the report says critical/urgent or you have severe or rapidly worsening symptoms, contact a qualified healthcare professional or local emergency service."
    )
else:
    st.markdown(
        "### How to use\n"
        "1. Upload a PDF or a scan/photo of a report.\n"
        "2. The app extracts selectable PDF text or uses OCR for scans.\n"
        "3. Review the extracted text for mistakes.\n"
        "4. For AI analysis, check the privacy consent box and click **Analyze report with AI**.\n"
        "5. Compare AI-extracted values and quotes with the original report before relying on them.\n\n"
        "### Setup and limitations\n"
        "- AI analysis requires an OpenAI API key and internet access; API usage is billed separately from a ChatGPT subscription.\n"
        "- OCR for scanned files requires the Tesseract application and the Python packages `pytesseract` and `Pillow`.\n"
        "- The built-in laboratory parser supports a limited set of test names; AI extraction is broader but not guaranteed complete or correct.\n"
        "- The app reads the written report, not medical image pixels, and does not diagnose or recommend treatment.\n"
        "- Avoid uploading reports unless you are comfortable sending extracted text to the configured AI provider."
    )


st.divider()
render_context_voice_assistant()
st.divider()
with st.expander("Local report history (stored on this computer)", expanded=False):
    st.warning("History contains sensitive report text and AI output. It is stored in a local SQLite file next to this app. Use only on a trusted computer; delete records when no longer needed.")
    try:
        history_rows = read_history()
        if not history_rows:
            st.info("No saved analyses yet. Analyze a report, then click 'Save this analysis to local history'.")
        else:
            options = {f"#{r[0]} · {r[1]} · {r[2]} · {r[3]}": r[0] for r in history_rows}
            selected_label = st.selectbox("Saved analysis", list(options.keys()), key="history_record_select")
            record = get_history_record(options[selected_label])
            if record:
                st.markdown(f"**File:** {record[2]}  ·  **Saved:** {record[1]}  ·  **Language:** {record[3]}")
                try:
                    saved_json = json.loads(record[5])
                    st.write(saved_json.get("plain_language_summary", "No summary stored."))
                    saved_labs = saved_json.get("laboratory_results") or []
                    if saved_labs:
                        st.dataframe([{
                            "Parameter": x.get("parameter", ""), "Value": x.get("value", ""), "Unit": x.get("unit", ""),
                            "Reference range": x.get("reference_range", ""), "Status as reported": x.get("status_as_reported", ""),
                            "Range-based check": classify_numeric_range(x.get("value", ""), x.get("reference_range", ""))
                        } for x in saved_labs if isinstance(x, dict)], use_container_width=True, hide_index=True)
                except Exception:
                    st.text(record[5])
                st.download_button("Download saved AI analysis (JSON)", data=record[5], file_name=f"saved_analysis_{record[0]}.json", mime="application/json", key=f"history_download_{record[0]}")
                if st.button("Delete this saved record", key=f"history_delete_{record[0]}"):
                    delete_history_record(record[0])
                    st.success("Saved record deleted.")
                    st.rerun()
    except Exception as exc:
        st.error(f"Could not read local history: {type(exc).__name__}: {exc}")
