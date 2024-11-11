import plotly.graph_objects as go

def generate_food_record_plot(entries: dict, target=0, show=False):
    x_keys = list(entries.keys())
    y_total_eaten_minus_burned = []
    y_total_burned = []
    for val in entries.values():
        cur_total_wo_burn = 0
        cur_total_burn = 0
        for f in val["food"]:
            cur_total_wo_burn += f["calories"]
        for e in val["exercise"]:
            cur_total_burn += e["calories"]
            cur_total_wo_burn -= e["calories"]
        y_total_eaten_minus_burned.append(cur_total_wo_burn)
        y_total_burned.append(cur_total_burn)

    fig = go.Figure(data=[
        go.Bar(name='Eaten', x=x_keys, y=y_total_eaten_minus_burned, marker_color="red"),
        go.Bar(name='Burned', x=x_keys, y=y_total_burned, marker_color="green")
    ])

    fig.add_shape( #adds line for the target calory count
        type="line",
        x0=0, x1=1,  # x0 and x1 as fractions (0-1) of the x-axis to cover entire width
        y0=target, y1=target,
        line=dict(color="black", width=2, dash="solid"),
        xref="paper",  # Use "paper" to span the entire x-axis
        yref="y"
    )

    fig.add_trace(go.Scatter( #empty dummy plot to get extra entry to the legend for target line (note to self: all the set attributes need to be present in order to get it look correct in the legend)
        x=[None], y=[None],
        name="Target",
        line=dict(color="black", width=2, dash="solid"),
        mode="lines"
    ))

    fig.update_layout(barmode='stack')
    if show:
        fig.show()
    else:
        return fig.to_html(full_html=False)

if __name__ == "__main__":
    test_data = {'4.11.2024': {'food': [], 'exercise': []}, '5.11.2024': {'food': [], 'exercise': []}, '6.11.2024': {'food': [], 'exercise': []}, '7.11.2024': {'food': [], 'exercise': []}, '8.11.2024': {'food': [], 'exercise': []}, '9.11.2024': {'food': [{'datetime': 1731162944, 'food': 'perse', 'calories': 0.0, 'note': ''}, {'datetime': 1731162945, 'food': 'pillu', 'calories': 0.0, 'note': ''}, {'datetime': 1731187255, 'food': 'option2', 'calories': 223.2, 'note': 'from rec'}, {'datetime': 1731187840, 'food': 'omena', 'calories': 123.0, 'note': ''}, {'datetime': 1731188249, 'food': 'brusa', 'calories': 1234.0, 'note': ''}, {'datetime': 1731188254, 'food': 'omena', 'calories': 123.0, 'note': ''}], 'exercise': [{'datetime': 1731187433, 'calories': 123.0, 'desc': 'kävely'}]}, '10.11.2024': {'food': [], 'exercise': []}, '11.11.2024': {'food': [{'datetime': 1731350352, 'food': 'omena', 'calories': 123.0, 'note': ''}, {'datetime': 1731350355, 'food': 'brusa', 'calories': 1234.0, 'note': ''}, {'datetime': 1731350364, 'food': '3200', 'calories': 3222.0, 'note': ''}, {'datetime': 1731352997, 'food': 'omena', 'calories': 123.0, 'note': ''}], 'exercise': [{'datetime': 1731350369, 'calories': 1234.0, 'desc': '1234'}]}}
    generate_food_record_plot(test_data, 1234, True)