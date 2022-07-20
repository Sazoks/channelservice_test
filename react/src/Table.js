import React from "react";


export default function Table({ orders }) {

    return (
        <table className="table">
            <thead>
                <tr>
                    <th>№</th>
                    <th>заказ №</th>
                    <th>стоимость,$</th>
                    <th>срок поставки</th>
                    <th>стоимость,₽</th>
                </tr>
            </thead>
            <tbody>
                { orders.map(order => {
                    return (
                        <tr>
                            <td>{ order.number }</td>
                            <td>{ order.order_number }</td>
                            <td>{ order.dollars }</td>
                            <td>{ order.delivery_time }</td>
                            <td>{ order.rubles }</td>
                        </tr>
                    );
                }) }
            </tbody>
        </table>
    );
}
