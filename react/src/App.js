import React, {useEffect} from 'react';
import Loader from './Loader';
import Table from './Table';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';


function App() {
  const [orders, setOrders] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [max_dollars, setMaxDollars] = React.useState(0);
  const [total_dollars, setTotalDollars] = React.useState(0);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/googlesheets/orders/', {
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json',
       }
    }).then(response => response.json())
      .then(response => {
        setOrders(response.orders);
        let _max_dollars = max_dollars;
        response.orders.forEach(element => {
          let element_dollars = Number(element.dollars);
          if (element_dollars > _max_dollars) {
            _max_dollars = element_dollars;
          }
        });
        setMaxDollars(_max_dollars);
        setTotalDollars(response.total_dollars);
        setLoading(false);
      })
  }, []);

  return (
    <div className='wrapper'>
      <h1 className='main_header'>
        <img src='logo.png' />
      </h1>

      {loading && <Loader />}

      {orders.length ? (
        <ResponsiveContainer width="100%" aspect={3}>
          <LineChart
            data={orders}
            margin={{
              top: 15,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid  horizontal="true" vertical="" stroke="black"/>
            <XAxis dataKey="delivery_time" />
            <YAxis type="number" domain={[0, max_dollars]} />
            <Tooltip contentStyle={{ backgroundColor: "#f5f5f5", color: "gray", 
                      border: "1px solid silver", borderRadius: "8px" }} 
                      itemStyle={{ color: "gray" }} cursor={false}/>
            <Line type="monotone" dataKey="dollars" stroke="#1a8ef3" />
          </LineChart>
        </ResponsiveContainer>
      ) : loading ? null : (
        <p>Данных для графика нет.</p>
      )}

      <div>
        <h2>Total: { orders.length ? total_dollars + '$' : <p>Данных нет.</p>}</h2>
      </div>

      {orders.length ? (
        <Table orders={orders} />
      ) : loading ? null : (
        <p>Данных нет.</p>
      )}
    </div>
  );
}

export default App;
