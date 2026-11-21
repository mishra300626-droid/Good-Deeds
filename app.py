                    deed.get("category", "Uncategorised")
                    for deed in data["deeds"]
                )
            )

            history_filter = st.selectbox(
                "Filter history by category",
                history_categories,
            )

            filtered_history = data["deeds"]

            if history_filter != "All Categories":

                filtered_history = [
                    deed
                    for deed in data["deeds"]
                    if deed.get("category", "Uncategorised")
                    == history_filter
                ]

            for deed in filtered_history:

                earned = int(deed.get("points", 0) or 0)
                point_summary = f"+{earned} bonus points" if earned else "recorded without points"
                st.write(f"**{deed.get('name', 'Good deed')}** — {point_summary}")

                st.caption(
                    f"{deed.get('category', '')} • "
                    f"{deed.get('date', '')} • "
                    f"{deed.get('description', '')}"
                )

                st.divider()

        else:

            st.info(
                "No deeds have been recorded yet."
            )

        with st.expander("📜 Approval Review History"):
            child_review_history = data.get("child_deed_request_history", [])
            reward_review_history = data.get("reward_request_history", [])
            if child_review_history:
                st.markdown("**Child deed submissions**")
                for request in child_review_history[:20]:
                    st.write(f'**{request.get("name", "Good deed")}** — {request.get("status", "Reviewed")}')
                    if request.get("review_note"):
                        st.caption("Note: " + request["review_note"])
                    st.caption(request.get("reviewed_at", ""))
            if reward_review_history:
                st.markdown("**Reward requests**")
                for request in reward_review_history[:20]:
                    st.write(f'🎁 **{request.get("reward", "Reward")}** — {request.get("status", "Reviewed")} ({request.get("cost", 0)} ⭐)')
                    if request.get("review_note"):
                        st.caption("Note: " + request["review_note"])
                    st.caption(request.get("reviewed_at", ""))
            if not child_review_history and not reward_review_history:
                st.caption("No requests have been reviewed yet.")

        st.divider()



    with parent_settings_tab:
        st.caption("Change the Parent Dashboard password here. For appearance, goals, motivation, accessibility, and auto-lock preferences, open the ⋮ Settings menu at the top-right.")
        st.subheader(
            "🔑 Change Parent Dashboard Password"
        )

        with st.form(
            "change_parent_password_form"
        ):

            current_password = st.text_input(
                "Current Parent Dashboard Password",
                type="password",
            )

            new_password = st.text_input(
                "New Parent Dashboard Password",
                type="password",
            )

            confirm_password = st.text_input(
                "Confirm New Parent Dashboard Password",
                type="password",
            )

            change_password = st.form_submit_button(
                "🔐 Change Parent Password"
            )

            if change_password:

                if not check_parent_password(
                    current_password
                ):

                    st.error(
                        "❌ Current Parent Dashboard password "
                        "is incorrect."
                    )

                elif len(new_password) < 8:

                    st.error(
                        "Please choose a new Parent Dashboard password "
                        "with at least 8 characters."
                    )

                elif new_password != confirm_password:

                    st.error(
                        "The two new passwords do not match."
                    )

                else:

                    data[
                        "parent_password_hash"
                    ] = hash_parent_password(
                        new_password
                    )

                    save_data(data)

                    st.success(
                        "✅ Parent Dashboard password "
                        "changed successfully."
                    )

        st.divider()


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "⭐ Good Deeds • Kindness matters, with or without points."
)
