import plotly.graph_objects as go
from scipy.stats import linregress
import math
from datetime import datetime

def generate_food_record_plot(entries: dict, target=0, show=False, html=False):
    x_keys = list(entries.keys())
    y_total_eaten_minus_burned = []
    y_total_burned = []
    avg_list = []
    for val in entries.values():
        cur_total_wo_burn = 0
        cur_total_burn = 0
        for f in val["food"]:
            cur_total_wo_burn += f["calories"]
        for e in val["exercise"]:
            cur_total_burn += e.calories
            cur_total_wo_burn -= e.calories
        y_total_eaten_minus_burned.append(cur_total_wo_burn)
        y_total_burned.append(cur_total_burn)
        if cur_total_wo_burn:
            avg_list.append(cur_total_wo_burn)

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

    fig.update_layout(barmode='stack',
                      margin=dict(l=20, r=20, t=20, b=20))
    
    # generate activity burn line
    y_activity_burns = []
    for key, val in entries.items():
        if val['activity']:
            y_activity_burns.append(val['activity'].calories)
        else:
            y_activity_burns.append(0)
    if any(y_activity_burns): # if we dont have polarflow integration enabled, there wont be any data so dont even try generating the line
        fig.add_trace(go.Scatter(
            name="Activity burn",
            x=x_keys, y=y_activity_burns,
            mode="lines+markers",
            line=dict(color="blue")
        ))
    
    if avg_list: #cant calculate if 0 records
        avg = round(sum(avg_list) / len(avg_list), 2)
    else:
        avg = 0

    if show:
        fig.show()
    else:
        if html:
            return fig.to_html(full_html=False), avg
        else:
            fig.update_layout(width=800) #TODO: somehow set the width in js
            return fig.to_plotly_json(), avg


def generate_weight_plot(entries: dict, target=0.0, show=False):
    x, y, x_epochs = [], [], []
    for entry in entries:
        x.append(datetime.fromtimestamp(entry["datetime"]))
        y.append(entry["weight"])
        x_epochs.append(entry["datetime"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='markers+lines', name="Weight"))

    slope, intercept, r_value, p_value, std_err = linregress(x_epochs, y)
    if not math.isnan(slope) and not math.isnan(intercept): #only generate these if there is valid values
        target_reached_estimate_ts = int((target - intercept) / slope)
        draw_estimate_plot = target_reached_estimate_ts > min(x_epochs) #we can only draw forecast if user is actually losing weight. TODO: if target is actually higher than start weight this should be the opposite
        target_reached_estimate_ts_overhot = target_reached_estimate_ts + 60*60*24 #overshoot by one day to make plot look nicer
        x_line = [datetime.fromtimestamp(min(x_epochs)),
                  datetime.fromtimestamp(target_reached_estimate_ts_overhot)]
        y_line = [slope * min(x_epochs) + intercept, slope * target_reached_estimate_ts_overhot + intercept]
        if draw_estimate_plot:
            fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name='Forecast'))
            fig.add_trace(go.Scatter(x=[datetime.fromtimestamp(target_reached_estimate_ts)], y=[target], mode='markers', name='Target reached date'))
    
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    if show:
        fig.show()
    else:
        return fig.to_html(full_html=False)


if __name__ == "__main__":
    #test_data = {'4.11.2024': {'food': [], 'exercise': []}, '5.11.2024': {'food': [], 'exercise': []}, '6.11.2024': {'food': [], 'exercise': []}, '7.11.2024': {'food': [], 'exercise': []}, '8.11.2024': {'food': [], 'exercise': []}, '9.11.2024': {'food': [{'datetime': 1731162944, 'food': 'perse', 'calories': 0.0, 'note': ''}, {'datetime': 1731162945, 'food': 'pillu', 'calories': 0.0, 'note': ''}, {'datetime': 1731187255, 'food': 'option2', 'calories': 223.2, 'note': 'from rec'}, {'datetime': 1731187840, 'food': 'omena', 'calories': 123.0, 'note': ''}, {'datetime': 1731188249, 'food': 'brusa', 'calories': 1234.0, 'note': ''}, {'datetime': 1731188254, 'food': 'omena', 'calories': 123.0, 'note': ''}], 'exercise': [{'datetime': 1731187433, 'calories': 123.0, 'desc': 'kävely'}]}, '10.11.2024': {'food': [], 'exercise': []}, '11.11.2024': {'food': [{'datetime': 1731350352, 'food': 'omena', 'calories': 123.0, 'note': ''}, {'datetime': 1731350355, 'food': 'brusa', 'calories': 1234.0, 'note': ''}, {'datetime': 1731350364, 'food': '3200', 'calories': 3222.0, 'note': ''}, {'datetime': 1731352997, 'food': 'omena', 'calories': 123.0, 'note': ''}], 'exercise': [{'datetime': 1731350369, 'calories': 1234.0, 'desc': '1234'}]}}
    #generate_food_record_plot(test_data, 1234, True)
    test_data = [{'datetime': 1731353511, 'weight': 56.0}, {'datetime': 1731439928, 'weight': 56.1}, {'datetime': 1731526363, 'weight': 55.5}]
    #test_data = [{'datetime': 1731353511, 'weight': 56.0}]
    generate_weight_plot(test_data, 40, True)