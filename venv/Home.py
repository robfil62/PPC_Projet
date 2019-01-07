from multiprocessing import Process,Queue,Lock,Value,Event
import time
import random
import multiprocessing

nmbHome=50
nmbTour=3
delai=10
def Home(ID,lockQueue,lockCount,queue,count,market_OK,lockWrite,clock_ok):
    Money_Bal = 0

    Id = ID
    while clock_ok.wait(1.5*delai):

        flag_Market = False
        neg_Flag = False

        ##Calcul Prod et Cons avec weather
        Prod = random.randrange(1, 5)
        Cons = random.randrange(1, 5)
        Energy_Bal = Prod - Cons  # Calcul de Energy_Balance pour chaque Home
        with lockWrite:
            print("Energy n°", Id, " : ", Energy_Bal)

        if Energy_Bal < 0:  # Si Home en déficit :
            with lockQueue:
                queue.put([Id, Energy_Bal])  # Met sa demande dans la queue
            with lockCount:
                count.value += 1  # Annonce qu'elle a terminé de remplir

        else:  # Sinon :
            with lockCount:
                count.value += 1  # Ne fais rien et annonce qu'elle a terminé de remplir

        while count.value < nmbHome:  # Attend que toutes les Homes aient rempli la queue avec les demandes
            True
        clock_ok.clear()


        if Energy_Bal > 0:  # Si la Home est en surplus :
            with lockQueue:
                while (Energy_Bal != 0 and (not queue.empty() or queue.qsize()!=0)):  # Tant qu'elle encore de l'énergie à donner et qu'il y a des demandes non traitées :
                    demande = queue.get()
                    if abs(demande[1]) <= Energy_Bal:  # Si la demande est réalisable:
                        Energy_Bal = Energy_Bal - abs(demande[1])  # Donne son énergie à la maison
                        with lockWrite:
                            print("Maison n° ", Id, "donne ", abs(demande[1]), "à maison", demande[0])
                    else:  # Si la demande est trop importante :
                        queue.put([demande[0],demande[1] + Energy_Bal])  # Donne son énergie restante et replace la demande mise à jour
                        with lockWrite:
                            print("Maison n° ",Id,"donne",Energy_Bal, "à maison",demande[0])
                        Energy_Bal = 0  # Son énergie devient nulle


        with lockCount:
            count.value += 1  # Annonce qu'elle a fini de donner son énergie

        while count.value < 2 * nmbHome:  # Attend toutes les Homes
            True

        if Energy_Bal < 0: # Si la Home est en déficit, regarde si quelqu'un à répondu à sa demande :
            Tab=[]
            with lockQueue:
                while not queue.empty() or queue.qsize()!=0 : # Tant que la queue n'est pas vide
                    demande = queue.get()
                    if demande[0] == Id:  # Regarde si la demande nous concerne
                        Energy_Bal = demande[1]  # Si oui, met à jour son Energy_Bal
                        neg_Flag = True
                        break
                    else:
                        Tab.append(demande)

                for d in Tab:
                    queue.put(d)

            if neg_Flag == False:  # Si la queue est vide et qu'elle n'a pas trouvé de demande la concernant
                Energy_Bal = 0  # Sa demande a été traitée entiérement, donc Energy_Bal passe à 0


        if Energy_Bal != 0:
            with lockQueue:
                queue.put([Id, Energy_Bal])
                flag_Market = True
            Energy_Bal = 0


        with lockCount:
            count.value += 1  # Annonce qu'elle est prête


        neg_Flag = False







        ########## A ce stade, la queue ne contient que des demandes et des offres pour le marché ##########

        while market_OK.value == False:
            True

        if flag_Market :
            Tab2=[]
            with lockQueue:
                while flag_Market == True:
                    demande = queue.get()
                    if demande[0] == Id:
                        Money_Bal += demande[1]
                        flag_Market = False
                    else:
                        Tab2.append(demande)

                for d in Tab2:
                    queue.put(d)

        count.value=0

        with lockWrite:
            print("Money n°", Id, " : ", Money_Bal)
        ###Wait clock







def Market(queue,count,market_OK,clock_ok):
    while clock_ok.wait(1.5*delai):
        currentPrice=10
        market_OK.value=False

        while count.value<3*nmbHome:
            True
        size=queue.qsize()
        for i in range(0,size):
            demande=queue.get()
            queue.put([demande[0],demande[1]*currentPrice])

        market_OK.value=True

def Clock(clock_ok,):
    c=0
    while c<nmbTour:
        clock_ok.set()
        c+=1
        temps=time.time()
        while time.time()-temps<delai:
            time.sleep(2)
        print("**********************************")


if __name__=="__main__":
    ti=time.time()
    lockQueue = Lock()
    lockCount=Lock()
    lockWrite=Lock()
    queue=Queue()
    count=Value('i',0)
    clock_ok=Event()
    Homes=[]
    market_OK=Value('b',False)
    c = Process(target=Clock, args=(clock_ok, ))
    c.start()

    for i in range(1,nmbHome+1):
        h=Process(target=Home, args=(i,lockQueue,lockCount,queue,count,market_OK,lockWrite,clock_ok),)
        h.start()
        Homes.append(h)
    m=Process(target=Market, args=(queue,count,market_OK,clock_ok))
    m.start()

    c.join()
    m.join()
    for h in Homes:
        h.join()



    print("temps de la simulation:",time.time()-ti)






