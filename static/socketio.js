document.addEventListener('DOMContentLoaded', () =>{
    var socket = io.connect('http://'+ document.domain +':'+ location.port);

    let room;

    // Displays the messages
    socket.on('message',data => {
        const p = document.createElement('p');
        const span_username = document.createElement('span');
        const br = document.createElement('br');
        span_username.innerHTML = data.username;
        p.innerHTML = span_username.outerHTML + br.outerHTML + data.msg + br.outerHTML;
        document.querySelector('#display-message-section').append(p);
    });

    // send message
    document.querySelector('#send_message').onclick = () => {
        socket.send({'msg': document.querySelector('#user_message').value,
            'username': username, 'room': room });
    };

    // room selection
    //querySelectorAll
    document.querySelectorAll('.select-room').forEach(p => {
        p.onclick = () => {
            let newRoom = p.innerHTML;
            if (newRoom == room) {
                msg = `You are already in ${room} room.`
                printSysMsg(msg);
            } else {
                leaveRoom(room);
                joinRoom(newRoom);
                room = newRoom;
            }
        }
    });

    //leave room
    function leaveRoom(room) {
        socket.emit('leave', {'username': username, 'room': room});
    }

    // join room
    function joinRoom(room){
        socket.emit('join', {'username': username, 'room':room});
        //Ckear message area
        document.querySelector('#display-message-section').innerHTML = ''
    }

    // Print system messages
    function printSysMsg(msg) {
        const p = document.createElement('p');
        p.innerHTML= msg;
        document.querySelector('#display-message-section').append(p);
    }

});